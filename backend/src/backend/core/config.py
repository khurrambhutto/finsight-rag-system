from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RAG System API"
    app_env: str = "development"
    sqlite_path: str = "data/rag-system.db"
    clerk_secret_key: str = ""
    clerk_jwt_key: str | None = None
    clerk_authorized_parties: list[str] = Field(default_factory=list)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "ollama/gemma4:e2b"
    provider_name: str = "Local Ollama"
    provider_type: str = "ollama"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
