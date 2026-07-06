"""Orchestrator builder — wires model, tools, skills, and MCP into one Agent.

Usage:
    from demo.orchestrator import build_orchestrator

    agent = build_orchestrator(model)            # native (pydantic-ai + MCP)
    agent = build_orchestrator(model, "wmt")     # WmtAgent MVP (no MCP)
    async with agent:
        result = await agent.run(prompt)
"""
from __future__ import annotations

import sys
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset
from fastmcp.client.transports import PythonStdioTransport

sys.path.insert(0, str(Path(__file__).parent.parent))
from wmt_ai.agent import AgentBuilder
from wmt_ai.logger import get_logger
from demo.schemas import OrchestratorResult
from demo.skills import knowledge_skill
from demo.tools import register_tools

_log = get_logger("ORCH")

_MCP_SCRIPT = Path(__file__).parent / "mcp_server.py"


_INSTRUCTIONS = (
    "You are an orchestrator agent. For the given request you MUST use "
    "ALL of the following in a single response:\n"
    "  • calculate      — for any arithmetic\n"
    "  • search_knowledge / word_count  — from the knowledge skill\n"
    "  • get_current_time / get_fact    — from the MCP server\n"
    "  • research_and_write             — to delegate to sub-agents\n"
    "Summarise what you did and list every tool you called in 'steps_used'."
)


def build_orchestrator(model, backend: str = "native") -> Agent:
    """Construct and return the fully-wired orchestrator Agent.

    Args:
        model:   A pydantic-ai Model (from wmt_ai.models.create_model).
        backend: 'native' (pydantic-ai Agent, default) or 'wmt' (WmtAgent MVP).
                 Note: MCP is only supported with backend='native'.

    Returns:
        An agent ready to use as ``async with agent:`` + ``await agent.run(prompt)``.
    """
    _log.debug(f"Building orchestrator  model={model!r}  backend={backend!r}")

    mcp_server = MCPToolset(PythonStdioTransport(script_path=str(_MCP_SCRIPT)))
    _log.debug(f"MCP toolset configured  script={_MCP_SCRIPT.name}")

    builder = AgentBuilder(
        model=model,
        output_type=OrchestratorResult,
        instructions=_INSTRUCTIONS,
    )

    register_tools(builder, model)           # tools/calculate + tools/research
    builder.with_skill(knowledge_skill)      # skills/knowledge_skill
    builder.with_mcp(mcp_server)             # MCP subprocess

    agent = builder.build(backend=backend)
    _log.debug("Orchestrator ready")
    return agent
