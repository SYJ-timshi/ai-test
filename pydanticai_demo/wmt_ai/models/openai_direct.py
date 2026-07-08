"""Direct OpenAI API model factory.

Required env vars:
    OPENAI_API_KEY - Your OpenAI API key
"""
from pydantic_ai.models.openai import OpenAIResponsesModel


def create_openai_model(model_name: str = "gpt-4o-mini") -> OpenAIResponsesModel:
    """Return an OpenAIResponsesModel using the official OpenAI API directly."""
    return OpenAIResponsesModel(model_name)
