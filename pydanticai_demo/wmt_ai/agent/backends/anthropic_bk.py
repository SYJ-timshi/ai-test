"""AnthropicBackend — calls Anthropic's Messages API directly.

Wire format handled here so WmtAgent stays provider-agnostic:
  • tool schemas  → Anthropic tool definitions
  • tool_use blocks → ToolCall objects
  • usage fields  → LLMResponse.{input,output}_tokens
"""
from __future__ import annotations

from anthropic import AsyncAnthropic

from .base import LLMBackend, LLMResponse, ToolCall, ToolSchema


class AnthropicBackend:
    """Thin wrapper over AsyncAnthropic that speaks the LLMBackend protocol."""

    def __init__(self, client: AsyncAnthropic, model_name: str, max_tokens: int = 4096):
        self._client = client
        self._model = model_name
        self._max_tokens = max_tokens

    # ── LLMBackend protocol ─────────────────────────────────────────────────

    async def call(
        self,
        messages: list[dict],
        tools: list[ToolSchema],
        system: str = "",
    ) -> LLMResponse:
        """Translate to Anthropic wire format, call the API, translate back."""

        kwargs: dict = dict(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [self._to_anthropic_tool(t) for t in tools]

        raw = await self._client.messages.create(**kwargs)

        text = next(
            (block.text for block in raw.content if block.type == "text"), None
        )
        tool_calls = [
            ToolCall(id=block.id, name=block.name, input=dict(block.input))
            for block in raw.content
            if block.type == "tool_use"
        ]

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            input_tokens=raw.usage.input_tokens,
            output_tokens=raw.usage.output_tokens,
        )

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_anthropic_tool(schema: ToolSchema) -> dict:
        """Convert a ToolSchema to Anthropic's tool definition format."""
        return {
            "name": schema.name,
            "description": schema.description,
            "input_schema": schema.parameters,
        }

    @classmethod
    def from_pydantic_ai_model(cls, model) -> "AnthropicBackend":
        """Convenience constructor: extract client + model_name from a pydantic-ai AnthropicModel."""
        return cls(client=model.client, model_name=model.model_name)
