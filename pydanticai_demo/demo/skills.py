"""Knowledge skill — a FunctionToolset bundling offline knowledge-base tools.

'Skill' in this codebase = a FunctionToolset: a named group of related tools
that can be attached to any agent via AgentBuilder.with_skill().

Tools exposed:
  • search_knowledge(query)  — look up a topic in the local KB
  • word_count(text)         — count words in a string
"""
import sys
from pathlib import Path

from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset

sys.path.insert(0, str(Path(__file__).parent.parent))
from wmt_ai.logger import get_logger, entry, exit_

_log = get_logger("SKILL")

_KB: dict[str, str] = {
    "pydantic-ai": (
        "Pydantic AI is a production-grade agentic framework built on Pydantic. "
        "It supports structured outputs, tool calls, MCP, sub-agents, and streaming."
    ),
    "walmart": (
        "Walmart is the world's largest retailer by revenue, operating over 10,500 "
        "stores across 19 countries and serving 240 million customers weekly."
    ),
    "mcp": (
        "Model Context Protocol (MCP) is an open standard for connecting AI models "
        "to external tools and data sources via a lightweight JSON-RPC protocol."
    ),
    "agent": (
        "An AI agent is an autonomous system that perceives its environment, "
        "reasons about it, and takes actions to achieve a goal — potentially calling "
        "tools, spawning sub-agents, or maintaining state across turns."
    ),
    "pydantic": (
        "Pydantic is a Python data validation library using type annotations. "
        "It is the most widely downloaded Python package on PyPI."
    ),
}


def search_knowledge(ctx: RunContext, query: str) -> str:
    """Search the internal knowledge base for a topic.

    Args:
        query: Topic name or keywords to search for (e.g. 'pydantic-ai', 'mcp')
    """
    entry(_log, "SKILL", "search_knowledge", query=query)

    q = query.lower().strip()
    if q in _KB:
        result = _KB[q]
    else:
        matches = [v for k, v in _KB.items() if q in k or k in q]
        if matches:
            result = "\n\n".join(matches)
        else:
            found = next((v for k, v in _KB.items() if any(w in k for w in q.split())), None)
            result = found or (
                f"No knowledge found for '{query}'. "
                f"Available topics: {', '.join(_KB.keys())}"
            )

    exit_(_log, "SKILL", "search_knowledge", result)
    return result


def word_count(ctx: RunContext, text: str) -> int:
    """Count the number of words in a piece of text.

    Args:
        text: Any string whose words you want counted
    """
    entry(_log, "SKILL", "word_count", text=text[:60] + ("..." if len(text) > 60 else ""))
    count = len(text.split())
    exit_(_log, "SKILL", "word_count", count)
    return count


knowledge_skill = FunctionToolset(tools=[search_knowledge, word_count])
