"""
Application Configuration Module.
Uses Pydantic BaseSettings to parse, validate, and type environment variables.
"""

from functools import lru_cache
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App Metadata
    app_name: str = "Voyager AI - Agentic Travel Planner"
    api_prefix: str = "/api"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # LLM Settings
    llm_provider: Literal["gemini", "openai"] = "gemini"
    model_name: str = "gemini-3.6-flash"
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    temperature: float = 0.2

    # Observability (LangSmith)
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "travel-planner-agent"
    langchain_endpoint: str = "https://eu.api.smith.langchain.com"

    # Tools
    nominatim_user_agent: str = "voyager-travel-planner/1.0"
    http_timeout_seconds: float = 10.0


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached singleton instance of Settings."""
    return Settings()
