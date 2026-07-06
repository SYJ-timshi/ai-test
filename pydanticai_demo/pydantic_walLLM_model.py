"""Simple example of using Pydantic AI to construct a Pydantic model from a text input.

Uses Walmart LLM Gateway (no direct Claude API key needed).

Run with:

    uv run examples/pydantic_model.py

Required env vars (.env file):
    WMT_API_KEY    - Walmart LLM Gateway API key (JWT token)
    WMT_USER_EMAIL - Your Walmart email (e.g. tim.shi@walmart.com)
"""

import os
import ssl

import httpx
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

load_dotenv()

# ===== Walmart LLM Gateway config =====
WMT_GATEWAY_URL = "https://wmtllmgateway.stage.walmart.com/wmtllmgateway"
WMT_API_KEY = os.environ.get("WMT_API_KEY", "")
WMT_USER_EMAIL = os.environ.get("WMT_USER_EMAIL", "")

# Disable SSL verification for Walmart internal network
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
http_client = httpx.AsyncClient(verify=False)

anthropic_client = AsyncAnthropic(
    base_url=WMT_GATEWAY_URL,
    api_key=WMT_API_KEY,
    default_headers={
        "x-api-key": WMT_API_KEY,
        "wm_llm_gw.user_type": "ASSOCIATE",
        "wm_llm_gw.user_name": WMT_USER_EMAIL,
    },
    http_client=http_client,
)

provider = AnthropicProvider(anthropic_client=anthropic_client)
model = AnthropicModel("claude-opus-4-5", provider=provider)
# ======================================


class MyModel(BaseModel):
    city: str
    country: str


agent = Agent(model, output_type=MyModel)

if __name__ == '__main__':
    result = agent.run_sync('The windy city in the US of A.')
    print(result.output)
    print(result.usage)
