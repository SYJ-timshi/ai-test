"""Direct Anthropic API model factory.

Required env vars:
    ANTHROPIC_API_KEY - Your Anthropic API key
"""
from pydantic_ai.models.anthropic import AnthropicModel


def create_anthropic_model(model_name: str = "claude-opus-4-5") -> AnthropicModel:
    """Return an AnthropicModel using the official Anthropic API directly."""
    return AnthropicModel(model_name)
