"""Minimal FastMCP stdio server — launched as a subprocess by the demo agent.

Exposes two tools:
  • get_current_time()  — returns UTC ISO-8601 timestamp
  • get_fact(topic)     — returns a pre-baked fun fact (offline, no network)

Run standalone to test:
    python demo/mcp_server.py
"""
import datetime
import logging
import sys

from mcp.server.fastmcp import FastMCP

# ── subprocess logging → stderr (stdout is reserved for MCP JSON-RPC) ───────
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format="%(asctime)s  [MCP-SERVER] %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("mcp_server")

mcp = FastMCP("demo-mcp-server")

_FACTS: dict[str, str] = {
    "python": "Python was named after Monty Python's Flying Circus, not the snake.",
    "walmart": "Walmart was founded by Sam Walton in Rogers, Arkansas in 1962.",
    "ai": "The term 'Artificial Intelligence' was coined by John McCarthy in 1956.",
    "pydantic": "Pydantic validates data using Python type annotations at runtime.",
    "mcp": "Model Context Protocol was open-sourced by Anthropic in November 2024.",
}


@mcp.tool()
def get_current_time() -> str:
    """Return the current date and time in UTC as an ISO 8601 string."""
    _log.debug(">> get_current_time() called")
    result = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _log.debug(f"<< get_current_time() → {result!r}")
    return result


@mcp.tool()
def get_fact(topic: str) -> str:
    """Return a fun fact about a technology topic.

    Args:
        topic: One of: python, walmart, ai, pydantic, mcp
    """
    _log.debug(f">> get_fact(topic={topic!r}) called")
    key = topic.strip().lower()
    fact = _FACTS.get(key)
    if not fact:
        for k, v in _FACTS.items():
            if key in k or k in key:
                fact = v
                break
    result = fact or f"No fact available for '{topic}'. Try: {', '.join(_FACTS)}"
    _log.debug(f"<< get_fact(topic={topic!r}) → {result!r}")
    return result


if __name__ == "__main__":
    _log.debug("MCP server starting (transport=stdio)")
    mcp.run(transport="stdio")
