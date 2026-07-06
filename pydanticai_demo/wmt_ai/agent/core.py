"""WmtAgent — MVP agent that shows the core agentic loop from first principles.

Architecture
============

    user prompt
        │
        ▼
    ┌──────────────────────────────────────┐
    │  WmtAgent.run()                      │
    │                                      │
    │  messages = [system, user]           │
    │                                      │
    │  ┌─── loop (max_iterations) ───────┐ │
    │  │                                 │ │
    │  │  LLMBackend.call(msgs, tools)   │ │
    │  │         │                       │ │
    │  │    tool_calls?                  │ │
    │  │    ┌────┴────┐                  │ │
    │  │   YES        NO                 │ │
    │  │    │          │                 │ │
    │  │  execute    "final_result"      │ │
    │  │  tools       tool called?       │ │
    │  │  append       ┌────┴────┐       │ │
    │  │  results     YES        NO      │ │
    │  │    │          │         │       │ │
    │  │  loop      return    plain text │ │
    │  │  again     output    → parse    │ │
    │  └─────────────────────────────────┘ │
    └──────────────────────────────────────┘

Structured output
-----------------
WmtAgent injects a special ``final_result`` tool whose schema is the JSON Schema
of the requested output_type.  The LLM calls this tool to submit its final answer
— exactly the same technique pydantic-ai uses internally, just exposed here for
educational clarity.

Tool calling with ctx
---------------------
Tools written for pydantic-ai receive a ``RunContext`` as their first argument.
WmtAgent detects this by inspecting the signature and passes ``None`` in its
place — sufficient for the demo tools which never actually use the ctx value.
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints

from .backends.base import LLMBackend, LLMResponse, ToolSchema


# ── Result type ──────────────────────────────────────────────────────────────

@dataclass
class WmtAgentResult:
    """Mirrors the shape of pydantic-ai AgentRunResult so callers are identical."""
    output: Any
    usage: dict[str, int]
    messages: list[dict] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"WmtAgentResult(output={self.output!r}, "
            f"usage={self.usage})"
        )


# ── Agent ────────────────────────────────────────────────────────────────────

class WmtAgent:
    """Minimal agent — implements the agentic loop without any framework.

    Swap the backend (AnthropicBackend, OpenAIBackend, …) to change the LLM
    provider; the loop logic never changes.
    """

    def __init__(
        self,
        backend: LLMBackend,
        instructions: str = "",
        tools: list[Callable] = (),
        output_type: Any = str,
        max_iterations: int = 10,
    ):
        self._backend = backend
        self._instructions = instructions
        self._tools: dict[str, Callable] = {fn.__name__: fn for fn in tools}
        self._output_type = output_type
        self._max_iterations = max_iterations

    # ── public API (mirrors pydantic-ai Agent) ───────────────────────────────

    async def run(self, prompt: str) -> WmtAgentResult:
        """Run the agent loop until a final answer is produced."""
        messages: list[dict] = [{"role": "user", "content": prompt}]
        tool_schemas = self._build_tool_schemas()
        total_in = total_out = 0

        for iteration in range(self._max_iterations):
            response: LLMResponse = await self._backend.call(
                messages=messages,
                tools=tool_schemas,
                system=self._instructions,
            )
            total_in  += response.input_tokens
            total_out += response.output_tokens

            if not response.has_tool_calls:
                # Model gave text with no tool calls — parse as output and stop.
                output = self._parse_text_output(response.text or "")
                return WmtAgentResult(
                    output=output,
                    usage={"input_tokens": total_in, "output_tokens": total_out},
                    messages=messages,
                )

            # ── execute each tool call ────────────────────────────────────
            # Append the assistant turn (may contain text + tool_use blocks)
            assistant_content: list[dict] = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            for tc in response.tool_calls:
                assistant_content.append(
                    {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input}
                )
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute and collect results
            tool_results: list[dict] = []
            for tc in response.tool_calls:
                if tc.name == "_final_result":
                    # Structured output captured — build Pydantic model and return.
                    output = self._output_type(**tc.input)
                    return WmtAgentResult(
                        output=output,
                        usage={"input_tokens": total_in, "output_tokens": total_out},
                        messages=messages,
                    )

                content = await self._invoke_tool(tc.name, tc.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": tc.id, "content": content}
                )

            messages.append({"role": "user", "content": tool_results})

        raise RuntimeError(
            f"WmtAgent exceeded max_iterations={self._max_iterations} without producing output."
        )

    # ── async context manager (API compat with pydantic-ai Agent) ────────────

    async def __aenter__(self) -> "WmtAgent":
        return self

    async def __aexit__(self, *_: Any) -> None:
        pass  # nothing to clean up (MCP not supported in WmtAgent)

    # ── tool schema building ─────────────────────────────────────────────────

    def _build_tool_schemas(self) -> list[ToolSchema]:
        schemas = [self._introspect(fn) for fn in self._tools.values()]
        if self._output_type is not str:
            schemas.append(self._final_result_schema())
        return schemas

    def _introspect(self, fn: Callable) -> ToolSchema:
        """Build a ToolSchema from a function's signature and docstring."""
        sig = inspect.signature(fn)
        try:
            hints = get_type_hints(fn)
        except Exception:
            hints = {}

        properties: dict[str, dict] = {}
        required: list[str] = []
        param_docs = _parse_param_docs(inspect.getdoc(fn) or "")

        for name, param in sig.parameters.items():
            if name in ("self", "ctx"):    # skip pydantic-ai RunContext
                continue
            py_type = hints.get(name, str)
            prop: dict = {"type": _py_to_json_type(py_type)}
            if name in param_docs:
                prop["description"] = param_docs[name]
            properties[name] = prop
            if param.default is inspect.Parameter.empty:
                required.append(name)

        # First non-ctx/self line of the docstring → tool description
        raw_doc = inspect.getdoc(fn) or ""
        description = raw_doc.split("\n")[0].strip()

        return ToolSchema(
            name=fn.__name__,
            description=description,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )

    def _final_result_schema(self) -> ToolSchema:
        """Inject a special tool that captures structured output from the LLM."""
        raw_schema = self._output_type.model_json_schema()
        # Strip $defs / title so it's a flat input_schema
        parameters = {
            "type": "object",
            "properties": raw_schema.get("properties", {}),
            "required": raw_schema.get("required", []),
        }
        return ToolSchema(
            name="_final_result",
            description=(
                "Submit the final structured result. "
                "Call this EXACTLY ONCE when you have finished all tool calls "
                "and are ready to return your answer."
            ),
            parameters=parameters,
        )

    # ── tool invocation ──────────────────────────────────────────────────────

    async def _invoke_tool(self, name: str, kwargs: dict) -> str:
        """Call a tool by name, handling ctx injection and errors."""
        fn = self._tools.get(name)
        if fn is None:
            return f"[Error] Unknown tool: {name!r}"

        # Detect whether the function expects a ctx as first positional arg
        sig = inspect.signature(fn)
        params = list(sig.parameters)
        takes_ctx = bool(params) and params[0] == "ctx"

        try:
            if takes_ctx:
                result = fn(None, **kwargs)   # pass None as ctx stub
            else:
                result = fn(**kwargs)

            if inspect.isawaitable(result):
                result = await result

            return str(result)
        except Exception as exc:
            return f"[Error in {name}] {exc}"

    # ── output parsing ────────────────────────────────────────────────────────

    def _parse_text_output(self, text: str) -> Any:
        """Last-resort: try to parse plain text as JSON if output_type is a model."""
        if self._output_type is str:
            return text
        try:
            return self._output_type(**json.loads(text))
        except Exception:
            return text  # return raw text rather than crashing


# ── helpers ──────────────────────────────────────────────────────────────────

def _py_to_json_type(py_type: Any) -> str:
    mapping = {str: "string", int: "integer", float: "number", bool: "boolean"}
    return mapping.get(py_type, "string")


def _parse_param_docs(docstring: str) -> dict[str, str]:
    """Extract 'param: description' pairs from a Google-style docstring Args block."""
    result: dict[str, str] = {}
    in_args = False
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped.lower() in ("args:", "arguments:", "parameters:"):
            in_args = True
            continue
        if in_args:
            if stripped and not stripped[0].isspace() and stripped.endswith(":"):
                break  # new section
            if ":" in stripped:
                param, _, desc = stripped.partition(":")
                result[param.strip()] = desc.strip()
    return result
