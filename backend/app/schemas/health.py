from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = Field(default="healthy", description="Current operational status")
    app_name: str = Field(description="Name of the service")
    version: str = Field(description="API service version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check invocation",
    )
    environment: str = Field(description="Deployment environment")

