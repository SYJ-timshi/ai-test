"""Orchestrator builder — wires model, tools, skills, and MCP into one Agent.

Usage:
    from demo.orchestrator import build_orchestrator

    # stdio only (default, auto-spawns subprocess)
    agent = build_orchestrator(model)

    # HTTP only (requires mcp_server_http.py running separately)
    agent = build_orchestrator(model, mcp_transport="http")

    # BOTH simultaneously — stdio tools + HTTP fun tools
    agent = build_orchestrator(model, mcp_transport="both")

    # WmtAgent MVP (no MCP)
    agent = build_orchestrator(model, backend="wmt")

    async with agent:
        result = await agent.run(prompt)

HTTP transport startup
----------------------
When mcp_transport="http" or "both" you MUST start the HTTP server first:

    Terminal 1:  uv run demo/mcp_server_http.py
    Terminal 2:  uv run demo/main.py --mcp both

HTTP server: http://127.0.0.1:8765/mcp
HTTP tools : roll_dice | random_joke | random_quote | word_scramble
Stdio tools: get_current_time | get_fact
"""
from __future__ import annotations

import sys
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset, MCPServerStreamableHTTP
from fastmcp.client.transports import PythonStdioTransport

sys.path.insert(0, str(Path(__file__).parent.parent))
from wmt_ai.agent import AgentBuilder
from wmt_ai.logger import get_logger
from demo.schemas import OrchestratorResult
from demo.skills import knowledge_skill
from demo.tools import register_tools

_log = get_logger("ORCH")

_MCP_SCRIPT   = Path(__file__).parent / "mcp_server.py"
_MCP_HTTP_URL = "http://127.0.0.1:8765/mcp"


_INSTRUCTIONS = (
    "You are an orchestrator agent. Use available tools to complete the user's request.\n"
    "\n"
    "Stdio MCP tools (always available):\n"
    "  • get_current_time  — UTC timestamp\n"
    "  • get_fact(topic)   — tech fun facts\n"
    "\n"
    "HTTP MCP tools (available when --mcp http|both):\n"
    "  • roll_dice(sides, count)   — random dice roll\n"
    "  • random_joke(category)     — joke: programming|dad|general\n"
    "  • random_quote(mood)        — quote: motivational|funny|wisdom\n"
    "  • word_scramble(text)       — scramble word middles\n"
    "\n"
    "Other tools:\n"
    "  • calculate                 — arithmetic\n"
    "  • search_knowledge          — internal knowledge base\n"
    "  • research_and_write        — delegate to sub-agents\n"
    "\n"
    "Summarise what you did and list every tool you called in 'steps_used'."
)


def build_orchestrator(
    model,
    backend: str = "native",
    mcp_transport: str = "stdio",
) -> Agent:
    """Construct and return the fully-wired orchestrator Agent.

    Args:
        model:         A pydantic-ai Model (from wmt_ai.models.create_model).
        backend:       'native' (pydantic-ai Agent, default) or 'wmt' (WmtAgent MVP).
                       Note: MCP is only supported with backend='native'.
        mcp_transport: Transport(s) for MCP servers:
                       'stdio'  — stdio subprocess only (default)
                       'http'   — HTTP server only (must start mcp_server_http.py first)
                       'both'   — stdio + HTTP simultaneously

    Returns:
        An agent ready to use as ``async with agent:`` + ``await agent.run(prompt)``.
    """
    _log.debug(
        f"Building orchestrator  model={model!r}  backend={backend!r}"
        f"  mcp_transport={mcp_transport!r}"
    )

    builder = AgentBuilder(
        model=model,
        output_type=OrchestratorResult,
        instructions=_INSTRUCTIONS,
    )

    register_tools(builder, model)       # tools/calculate + tools/research
    builder.with_skill(knowledge_skill)  # skills/knowledge_skill

    # ── MCP server(s) ─────────────────────────────────────────────────────────
    use_stdio = mcp_transport in ("stdio", "both")
    use_http  = mcp_transport in ("http",  "both")

    if use_stdio:
        stdio_server = MCPToolset(PythonStdioTransport(script_path=str(_MCP_SCRIPT)))
        builder.with_mcp(stdio_server)
        _log.debug(f"MCP stdio  script={_MCP_SCRIPT.name}")

    if use_http:
        http_server = MCPServerStreamableHTTP(_MCP_HTTP_URL)
        builder.with_mcp(http_server)
        _log.debug(f"MCP http   url={_MCP_HTTP_URL}")

    if not use_stdio and not use_http:
        raise ValueError(
            f"Unknown mcp_transport={mcp_transport!r}. Choose: 'stdio' | 'http' | 'both'."
        )

    agent = builder.build(backend=backend)
    _log.debug("Orchestrator ready")
    return agent
