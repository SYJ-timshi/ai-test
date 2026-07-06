"""Shared Pydantic output schemas for the demo orchestrator."""
from pydantic import BaseModel, Field


class OrchestratorResult(BaseModel):
    summary: str = Field(
        description="High-level summary of what the agent accomplished"
    )
    steps_used: list[str] = Field(
        description="List of tools/capabilities used, e.g. ['calculate', 'MCP:get_fact']"
    )
