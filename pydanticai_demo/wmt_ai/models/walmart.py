"""Walmart LLM Gateway model factory.

Required env vars (.env):
    WMT_API_KEY    - JWT token from Walmart LLM Gateway
    WMT_USER_EMAIL - Your Walmart email (e.g. you@walmart.com)
"""
import os
import httpx
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

load_dotenv()

WMT_GATEWAY_URL = "https://wmtllmgateway.stage.walmart.com/wmtllmgateway"


def create_walmart_model(model_name: str = "claude-opus-4-5") -> AnthropicModel:
    """Return an AnthropicModel routed through the Walmart LLM Gateway."""
    api_key = os.environ.get("WMT_API_KEY", "")
    user_email = os.environ.get("WMT_USER_EMAIL", "")

    if not api_key:
        raise EnvironmentError("WMT_API_KEY is not set. Add it to your .env file.")
    if not user_email:
        raise EnvironmentError("WMT_USER_EMAIL is not set. Add it to your .env file.")

    http_client = httpx.AsyncClient(verify=False)  # internal corp network

    client = AsyncAnthropic(
        base_url=WMT_GATEWAY_URL,
        api_key=api_key,
        default_headers={
            "x-api-key": api_key,
            "wm_llm_gw.user_type": "ASSOCIATE",
            "wm_llm_gw.user_name": user_email,
        },
        http_client=http_client,
    )

    provider = AnthropicProvider(anthropic_client=client)
    return AnthropicModel(model_name, provider=provider)
