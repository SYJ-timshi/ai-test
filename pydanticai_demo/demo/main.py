"""Demo entry point — CLI parsing, run, print results. Nothing else.

Run:
    uv run demo/main.py                                   # walmart + native
    uv run demo/main.py --provider anthropic              # Anthropic + native
    uv run demo/main.py --provider openai                 # OpenAI + native
    uv run demo/main.py --provider deepseek               # DeepSeek + native
    uv run demo/main.py --backend wmt                     # WmtAgent (no MCP)
    uv run demo/main.py --mcp http                        # HTTP MCP only (start mcp_server_http.py first)
    uv run demo/main.py --mcp both                        # stdio + HTTP simultaneously

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

WELCOME_PROMPT = """\
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


def _print_result(result) -> None:
    out: OrchestratorResult = result.output
    print("\n✅  RESULT")
    print("─" * 62)
    print(out.summary)
    print("\n🔧  STEPS USED")
    for step in out.steps_used:
        print(f"  • {step}")
    usage = result.usage if isinstance(result.usage, dict) else result.usage
    print(f"\n📊  Token usage: {usage}")


async def main() -> None:
    provider      = _parse_arg("--provider", "walmart")
    backend       = _parse_arg("--backend",  "native")
    mcp_transport = _parse_arg("--mcp",      "both")
    _log.debug(
        f"Initialising  provider={provider!r}  backend={backend!r}"
        f"  mcp={mcp_transport!r}"
    )

    model        = create_model(provider)
    orchestrator = build_orchestrator(model, backend=backend, mcp_transport=mcp_transport)

    print(f"\n{'═' * 62}")
    print(f"  PydanticAI Full-Capability Demo   provider={provider}  backend={backend}  mcp={mcp_transport}")
    print(f"{'═' * 62}\n")
    # print(f"Welcome prompt:\n{WELCOME_PROMPT}")
    print("─" * 62)

    message_history = None

    _log.debug("Starting orchestrator ...")
    async with orchestrator:
        # 首轮：运行欢迎演示 prompt
        _log.debug("Running welcome prompt ...")
        # result = await orchestrator.run(WELCOME_PROMPT)
        # _print_result(result)
        # message_history = result.all_messages()
        message_history = list()
        # 持续监听用户输入
        print(f"\n{'─' * 62}")
        print("  Chat mode — type your message (exit/quit/Ctrl+D to stop)")
        print(f"{'─' * 62}")

        while True:
            try:
                user_input = (await asyncio.to_thread(input, "\n> ")).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if user_input.lower() in {"", "exit", "quit"}:
                print("Bye!")
                break

            _log.debug(f"User input: {user_input!r}")
            result = await orchestrator.run(user_input, message_history=message_history)
            _print_result(result)
            message_history = result.all_messages()

    _log.debug("Session ended")


if __name__ == "__main__":
    asyncio.run(main())
