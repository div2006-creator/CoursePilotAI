"""Agent Orchestrator interface.

Orchestrates multi-step reasoning, retrieval tools, and LLM calls.
Implementation will be added in subsequent milestones.
"""
from typing import Optional
from app.config import settings
from app.agents.state import AgentState


class AgentOrchestrator:
    """Coordinates tool execution, RAG context injection, and local Ollama model generation."""

    def __init__(self, model_name: Optional[str] = None, base_url: Optional[str] = None):
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.base_url = base_url or settings.OLLAMA_BASE_URL

    async def execute(self, state: AgentState) -> AgentState:
        """Executes the agentic loop against the provided AgentState.

        To be implemented in AI milestone.
        """
        raise NotImplementedError(
            "Agent orchestrator workflow execution will be implemented in subsequent AI milestone."
        )

