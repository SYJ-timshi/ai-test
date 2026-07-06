"""Demo entry point — CLI parsing, run, print results. Nothing else.

Run:
    uv run demo/main.py                                   # walmart + native
    uv run demo/main.py --provider anthropic              # Anthropic + native
    uv run demo/main.py --provider openai                 # OpenAI + native
    uv run demo/main.py --provider deepseek               # DeepSeek + native
    uv run demo/main.py --backend wmt                     # WmtAgent (no MCP)

Required env vars (.env):
    WMT_API_KEY / WMT_USER_EMAIL   (walmart)
    ANTHROPIC_API_KEY              (anthropic)
    OPENAI_API_KEY                 (openai)
    DEEPSEEK_API_KEY               (deepseek)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from wmt_ai.models import create_model
from wmt_ai.logger import get_logger
from demo.orchestrator import build_orchestrator
from demo.schemas import OrchestratorResult

_log = get_logger("ORCH")

DEMO_PROMPT = """\
Please complete ALL of the following in one response:
1. What is the current UTC time? (use MCP: get_current_time)
2. Calculate: 42 * 1337  (use calculate tool)
3. Search the knowledge base for 'pydantic-ai'  (use knowledge skill)
4. Get a fun fact about 'mcp'  (use MCP: get_fact)
5. Research and write a short article about 'Model Context Protocol' (use sub-agents)
Summarise everything and list every tool you used in 'steps_used'.
"""


def _parse_arg(flag: str, default: str) -> str:
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(f"{flag}="):
            return a.split("=", 1)[1]
    return default


async def main() -> None:
    provider = _parse_arg("--provider", "walmart")
    backend  = _parse_arg("--backend",  "native")
    _log.debug(f"Initialising  provider={provider!r}  backend={backend!r}")

    model        = create_model(provider)
    orchestrator = build_orchestrator(model, backend=backend)

    print(f"\n{'═' * 62}")
    print(f"  PydanticAI Full-Capability Demo   provider={provider}  backend={backend}")
    print(f"{'═' * 62}\n")
    print(f"Prompt:\n{DEMO_PROMPT}")
    print("─" * 62)

    _log.debug("Starting orchestrator ...")
    async with orchestrator:
        result = await orchestrator.run(DEMO_PROMPT)
    _log.debug("Run complete")

    out: OrchestratorResult = result.output
    print("\n✅  RESULT")
    print("─" * 62)
    print(out.summary)
    print("\n🔧  STEPS USED")
    for step in out.steps_used:
        print(f"  • {step}")

    # usage attr differs between native (pydantic-ai) and wmt (dict)
    usage = result.usage if isinstance(result.usage, dict) else result.usage
    print(f"\n📊  Token usage: {usage}")


if __name__ == "__main__":
    asyncio.run(main())
