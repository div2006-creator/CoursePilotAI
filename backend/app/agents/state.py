from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """Represents the shared working state of an agentic workflow execution.

    Used by the AgentOrchestrator to track session context, user intent,
    intermediate retrieved context chunks, and generated responses.
    """
    session_id: str = Field(description="Unique chat or planning session identifier")
    user_id: Optional[str] = Field(default=None, description="Active student identifier")
    course_id: Optional[str] = Field(default=None, description="Target course context")
    topic_id: Optional[str] = Field(default=None, description="Specific DSA topic focus")
    query: str = Field(default="", description="Current student prompt or problem statement")
    retrieved_context: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Relevant document chunks retrieved via vector similarity",
    )
    history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Conversation history formatted for the LLM",
    )
    final_response: Optional[str] = Field(
        default=None,
        description="Final validated output generated for the user",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution trace, tokens, and telemetry metadata",
    )

