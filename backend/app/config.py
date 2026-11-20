from pathlib import Path
from typing import Any, List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    # Application Configuration
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "CoursePilot AI API"
    APP_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production", ""}:
                return False
        return bool(v)

    # Security & JWT Authentication
    JWT_SECRET_KEY: str = "dev_insecure_jwt_secret_replace_with_32_byte_random_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        if not v or len(v.strip()) < 16:
            raise ValueError("JWT_SECRET_KEY must be at least 16 characters long")
        return v.strip()

    # CORS Configuration
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "coursepilot"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    DATABASE_URL: str | None = None
    TEST_DATABASE_URL: str | None = None

    @staticmethod
    def _normalize_db_url(url: str) -> str:
        """Ensure PostgreSQL URLs use the installed psycopg (v3) driver."""
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return self._normalize_db_url(self.DATABASE_URL)
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def test_database_url(self) -> str | None:
        if self.TEST_DATABASE_URL:
            return self._normalize_db_url(self.TEST_DATABASE_URL)
        return None

    # AI & LLM Services (Ollama & Local Embeddings)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_TIMEOUT_SECONDS: int = 90
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Document Uploads & Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    MAX_PDF_PAGES: int = 200
    MAX_UPLOAD_SIZE_BYTES: int | None = None

    @property
    def max_upload_size_bytes(self) -> int:
        if self.MAX_UPLOAD_SIZE_BYTES is not None and self.MAX_UPLOAD_SIZE_BYTES > 0:
            return self.MAX_UPLOAD_SIZE_BYTES
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def upload_dir_path(self) -> Path:
        raw = Path(self.UPLOAD_DIR)
        if raw.is_absolute():
            return raw.resolve()
        return (PROJECT_ROOT / raw).resolve()

    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

