"""Base protocol and data classes for LLM backends.

Architecture:
                        ┌─────────────┐
    WmtAgent  ─calls──► │ LLMBackend  │  (Protocol — swap freely)
                        └──────┬──────┘
                               │ implements
                    ┌──────────┴──────────┐
             AnthropicBackend        (future: OpenAIBackend ...)
             (uses AsyncAnthropic)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolSchema:
    """JSON-Schema description of one callable tool."""
    name: str
    description: str
    parameters: dict[str, Any]   # JSON Schema object


@dataclass
class ToolCall:
    """One tool invocation requested by the LLM."""
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    """Parsed response from a single LLM call."""
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class LLMBackend(Protocol):
    """Minimal protocol every backend must implement.

    WmtAgent depends only on this interface — swap the backend to change
    the underlying LLM provider without touching any agent logic.
    """

    async def call(
        self,
        messages: list[dict],
        tools: list[ToolSchema],
        system: str = "",
    ) -> LLMResponse:
        """Send messages to the LLM and return its response.

        Args:
            messages: Conversation history in provider-neutral dict format.
            tools:    Tool schemas available to the model this turn.
            system:   System-level instruction string (empty = none).
        """
        ...
