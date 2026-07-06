"""Tool registry — single call wires all tools into an AgentBuilder.

To add a new tool:
  1. Create demo/tools/my_tool.py  (plain function or factory)
  2. Import and register it here in register_tools()

Usage:
    from demo.tools import register_tools
    register_tools(builder, model)
"""
from .calculate import calculate
from .research import create_research_tool


def register_tools(builder, model) -> None:
    """Attach all demo tools to the given AgentBuilder.

    Args:
        builder: An AgentBuilder instance (from wmt_ai.agent).
        model:   The shared pydantic-ai Model — passed to tools that create sub-agents.
    """
    builder.with_tool(calculate)
    builder.with_tool(create_research_tool(model))
