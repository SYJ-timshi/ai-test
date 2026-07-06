"""DeepSeek model factory — uses DeepSeek's OpenAI-compatible API.

DeepSeek exposes an OpenAI-compatible endpoint, so we use OpenAIModel +
OpenAIProvider with a custom base_url and DEEPSEEK_API_KEY.

Available models:
    deepseek-chat      — DeepSeek-V3, general-purpose chat (default)
    deepseek-reasoner  — DeepSeek-R1, long chain-of-thought reasoning

Required env vars (.env):
    DEEPSEEK_API_KEY - Your DeepSeek API key (https://platform.deepseek.com)
"""
import os

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


def create_deepseek_model(model_name: str = "deepseek-chat") -> OpenAIModel:
    """Return an OpenAIModel routed to DeepSeek's API.

    Args:
        model_name: 'deepseek-chat' (V3, default) or 'deepseek-reasoner' (R1)
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY is not set. "
            "Get one at https://platform.deepseek.com and add it to your .env file."
        )

    provider = OpenAIProvider(
        base_url=DEEPSEEK_BASE_URL,
        api_key=api_key,
    )
    return OpenAIModel(model_name, provider=provider)
