"""LLM model factory — swap providers without touching agent code.

Usage:
    from wmt_ai.models import create_model

    model = create_model("walmart")                          # Walmart LLM Gateway (default)
    model = create_model("anthropic")                        # Anthropic API directly
    model = create_model("openai", "gpt-4o")                 # OpenAI with a specific model
    model = create_model("deepseek")                         # DeepSeek-V3 (chat)
    model = create_model("deepseek", "deepseek-reasoner")    # DeepSeek-R1 (reasoning)
"""
from __future__ import annotations

from typing import Literal
from pydantic_ai.models import Model

Provider = Literal["walmart", "anthropic", "openai", "deepseek"]

_DEFAULTS: dict[str, str] = {
    "walmart":   "claude-opus-4-5",
    "anthropic": "claude-opus-4-5",
    "openai":    "gpt-4o-mini",
    "deepseek":  "deepseek-chat",
}


def create_model(provider: Provider = "walmart", model_name: str | None = None) -> Model:
    """Return a pydantic-ai Model for the given provider.

    Args:
        provider:   One of 'walmart', 'anthropic', 'openai', 'deepseek'.
        model_name: Override the default model ID for this provider.

    Returns:
        A pydantic-ai compatible Model instance ready to pass to Agent().
    """
    name = model_name or _DEFAULTS[provider]

    if provider == "walmart":
        from .walmart import create_walmart_model
        return create_walmart_model(name)
    elif provider == "anthropic":
        from .anthropic_direct import create_anthropic_model
        return create_anthropic_model(name)
    elif provider == "openai":
        from .openai_direct import create_openai_model
        return create_openai_model(name)
    elif provider == "deepseek":
        from .deepseek import create_deepseek_model
        return create_deepseek_model(name)

    raise ValueError(
        f"Unknown provider '{provider}'. Choose from: walmart, anthropic, openai, deepseek"
    )


__all__ = ["create_model", "Provider"]
