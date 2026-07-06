"""Tool: research_and_write — delegates research + writing to sub-agents.

Uses a factory pattern because sub-agents need a model instance.

Usage:
    from demo.tools.research import create_research_tool
    tool = create_research_tool(model)   # returns a bound async callable
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from pydantic_ai import RunContext

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from wmt_ai.logger import get_logger, entry, exit_
from demo.subagents import create_researcher, create_writer, ResearchOutput

_log = get_logger("SUBAGENT")


def create_research_tool(model) -> Callable:
    """Return the research_and_write tool bound to freshly-created sub-agents.

    Args:
        model: A pydantic-ai Model — shared with the orchestrator so all agents
               use the same provider without re-initialising connections.
    """
    researcher = create_researcher(model)
    writer = create_writer(model)
    _log.debug(f"Sub-agents created (researcher, writer) for model={model!r}")

    async def research_and_write(ctx: RunContext, topic: str) -> str:
        """Research a topic and produce a short written article via sub-agents.

        Delegates to two agents sequentially:
          1. researcher_agent — returns structured findings + confidence score
          2. writer_agent     — turns findings into a titled article

        Args:
            topic: The subject to research and write about (e.g. 'Model Context Protocol')
        """
        entry(_log, "SUBAGENT", "research_and_write", topic=topic)

        # Step 1: researcher sub-agent
        _log.debug(f"[SUBAGENT]  >> researcher.run(topic={topic!r})")
        r_result = await researcher.run(f"Research this topic thoroughly: {topic}")
        findings: ResearchOutput = r_result.output
        _log.debug(
            f"[SUBAGENT]  << researcher done  "
            f"confidence={findings.confidence:.0%}  findings={len(findings.findings)}"
        )

        # Step 2: writer sub-agent
        bullet_points = "\n".join(f"- {f}" for f in findings.findings)
        _log.debug(f"[SUBAGENT]  >> writer.run(topic={topic!r}, findings={len(findings.findings)})")
        w_result = await writer.run(
            f"Write a short article about '{topic}' based on these findings:\n{bullet_points}"
        )
        article = w_result.output
        _log.debug(
            f"[SUBAGENT]  << writer done  "
            f"title={article.title!r}  words={article.word_count}"
        )

        result = (
            f"[Research complete — confidence: {findings.confidence:.0%}]\n\n"
            f"Title: {article.title}\n"
            f"Words: {article.word_count}\n\n"
            f"{article.body}"
        )
        exit_(_log, "SUBAGENT", "research_and_write", result)
        return result

    return research_and_write
