"""CoursePilot AI LLM and Embedding modules."""
from app.ai.llm import (
    LLMError,
    OllamaConnectionError,
    OllamaGenerationError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    check_ollama_status,
    generate_completion,
)

__all__ = [
    "LLMError",
    "OllamaConnectionError",
    "OllamaModelNotFoundError",
    "OllamaTimeoutError",
    "OllamaGenerationError",
    "check_ollama_status",
    "generate_completion",
]
