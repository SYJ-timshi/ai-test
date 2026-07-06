"""Direct OpenAI API model factory.

Required env vars:
    OPENAI_API_KEY - Your OpenAI API key
"""
from pydantic_ai.models.openai import OpenAIModel


def create_openai_model(model_name: str = "gpt-4o-mini") -> OpenAIModel:
    """Return an OpenAIModel using the official OpenAI API directly."""
    return OpenAIModel(model_name)
