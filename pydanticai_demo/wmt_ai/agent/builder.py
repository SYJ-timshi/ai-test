"""Fluent AgentBuilder — creates either a pydantic-ai Agent or a WmtAgent.

Usage:
    from wmt_ai.agent import AgentBuilder

    # Default: pydantic-ai Agent (full feature set, including MCP)
    agent = (
        AgentBuilder(model, instructions="You are helpful.")
        .with_tool(my_fn)
        .with_skill(my_toolset)
        .with_mcp(mcp_server)
        .build()                      # backend="native"
    )

    # WmtAgent: our own MVP agent (no MCP, shows the loop architecture)
    agent = (
        AgentBuilder(model, instructions="You are helpful.")
        .with_tool(my_fn)
        .with_skill(my_toolset)
        .build(backend="wmt")
    )

backend values
--------------
  "native"  pydantic-ai Agent  — full feature set (MCP, streaming, …)
  "wmt"     WmtAgent           — our MVP implementation, no MCP support
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import AbstractToolset, FunctionToolset

Backend = Literal["native", "wmt"]

# MCPToolset ⊂ AbstractToolset, so existing callers passing MCPToolset are unaffected.


@dataclass
class AgentBuilder:
    """Build a configurable agent with a readable fluent interface.

    Attributes:
        model:        A pydantic-ai Model (from wmt_ai.models.create_model).
        output_type:  Pydantic model or primitive for structured output (default: str).
        instructions: System-level instructions for the agent.
        deps_type:    Dependency injection type — native backend only.
    """

    model: Any
    output_type: Any = str
    instructions: str = ""
    deps_type: Any = type(None)

    _tools:       list[Callable]        = field(default_factory=list, init=False, repr=False)
    _toolsets:    list[AbstractToolset] = field(default_factory=list, init=False, repr=False)
    _mcp_servers: list[AbstractToolset] = field(default_factory=list, init=False, repr=False)

    # ── fluent API ───────────────────────────────────────────────────────────

    def with_tool(self, fn: Callable) -> "AgentBuilder":
        """Add a plain async or sync function as an inline tool."""
        self._tools.append(fn)
        return self

    def with_skill(self, toolset: AbstractToolset) -> "AgentBuilder":
        """Add a FunctionToolset (a named 'skill' grouping related tools)."""
        self._toolsets.append(toolset)
        return self

    def with_mcp(self, server: AbstractToolset) -> "AgentBuilder":
        """Add an MCP server toolset.  Only available with backend='native'.

        Accepts any AbstractToolset subclass: MCPToolset (stdio),
        MCPServerStreamableHTTP (HTTP), MCPServerSSE (SSE), etc.
        """
        self._mcp_servers.append(server)
        return self

    # ── build ────────────────────────────────────────────────────────────────

    def build(self, backend: Backend = "native") -> Agent | Any:
        """Construct and return the configured agent.

        Args:
            backend: 'native' (pydantic-ai Agent, default) or 'wmt' (WmtAgent MVP).

        Returns:
            An agent that supports ``async with agent:`` and ``await agent.run(prompt)``.
        """
        if backend == "native":
            return self._build_native()
        if backend == "wmt":
            return self._build_wmt()
        raise ValueError(f"Unknown backend {backend!r}. Choose 'native' or 'wmt'.")

    # ── native backend (pydantic-ai Agent) ───────────────────────────────────

    def _build_native(self) -> Agent:
        all_toolsets: list[Any] = self._toolsets + self._mcp_servers
        return Agent(
            self.model,
            output_type=self.output_type,
            instructions=self.instructions,
            deps_type=self.deps_type,
            tools=self._tools,
            toolsets=all_toolsets if all_toolsets else [],
        )

    # ── wmt backend (WmtAgent MVP) ────────────────────────────────────────────

    def _build_wmt(self):
        """Build a WmtAgent using AnthropicBackend extracted from the pydantic-ai model."""
        from .core import WmtAgent
        from .backends.anthropic_bk import AnthropicBackend

        if self._mcp_servers:
            import warnings
            warnings.warn(
                "WmtAgent does not support MCP servers — they will be ignored. "
                "Use backend='native' if you need MCP.",
                stacklevel=3,
            )

        backend = AnthropicBackend.from_pydantic_ai_model(self.model)

        # Flatten inline tools + skill functions into one list
        all_tools = list(self._tools) + self._extract_skill_fns()

        return WmtAgent(
            backend=backend,
            instructions=self.instructions,
            tools=all_tools,
            output_type=self.output_type,
        )

    def _extract_skill_fns(self) -> list[Callable]:
        """Pull the raw callables out of any FunctionToolsets attached as skills."""
        fns: list[Callable] = []
        for toolset in self._toolsets:
            if isinstance(toolset, FunctionToolset):
                for tool_obj in toolset.tools.values():
                    fns.append(tool_obj.function)
        return fns
