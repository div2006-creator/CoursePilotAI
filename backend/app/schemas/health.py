from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = Field(default="healthy", description="Current operational status: healthy, degraded, or unhealthy")
    app_name: str = Field(description="Name of the service")
    version: str = Field(description="API service version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check invocation",
    )
    environment: str = Field(description="Deployment environment")
    database: str = Field(default="connected", description="Database connectivity status")
    ollama: str = Field(default="connected", description="Ollama server connectivity status")
    model_available: bool = Field(default=True, description="Whether the configured LLM model is pulled")
    vector_extension: str = Field(default="available", description="Vector database extension availability")
    summary: Optional[str] = None
