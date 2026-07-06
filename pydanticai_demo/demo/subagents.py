"""Sub-agent definitions: researcher + writer.

These are plain pydantic-ai Agents returned by factory functions so they share
the same Model instance as the orchestrator (provider-agnostic).

Flow:
    orchestrator  →  research_and_write tool
                         ├→ researcher_agent  (ResearchOutput)
                         └→ writer_agent      (WritingOutput)
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent


# ── Structured outputs ──────────────────────────────────────────────────────

class ResearchOutput(BaseModel):
    topic: str = Field(description="The researched topic")
    findings: list[str] = Field(description="Key facts or findings, 3-5 bullet points")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score from 0.0 (uncertain) to 1.0 (very confident)",
    )


class WritingOutput(BaseModel):
    title: str = Field(description="A concise article title")
    body: str = Field(description="The article body, 3-4 sentences")
    word_count: int = Field(description="Approximate word count of the body")


# ── Agent factories (accept any pydantic-ai Model) ──────────────────────────

def create_researcher(model) -> Agent:
    """Return a research sub-agent that produces structured findings."""
    return Agent(
        model,
        output_type=ResearchOutput,
        instructions=(
            "You are a concise research agent. "
            "Given a topic, return 3-5 key findings as short bullet points "
            "and a confidence score (0.0–1.0). Be factual and brief."
        ),
    )


def create_writer(model) -> Agent:
    """Return a writer sub-agent that turns research findings into a short article."""
    return Agent(
        model,
        output_type=WritingOutput,
        instructions=(
            "You are a writing agent. "
            "Given a list of research findings, write a short, engaging article "
            "with a clear title and a 3-4 sentence body. "
            "Include an accurate word count for the body."
        ),
    )
