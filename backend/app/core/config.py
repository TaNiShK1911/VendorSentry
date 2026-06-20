"""
Application configuration via pydantic-settings.

All environment variables are read from .env at startup.
No secrets are ever hard-coded here — use .env.example as the template.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://vendorsentry:vendorsentry@localhost:5432/vendorsentry"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # LLM — Anthropic primary, Groq as fallback
    llm_api_key: str = ""
    llm_model: str = "claude-3-5-sonnet-20241022"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Auth
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 hours for hackathon

    # App
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # Scoring weights (must sum to 1.0 — validated in the scoring engine)
    weight_breach: float = 0.40
    weight_access: float = 0.25
    weight_compliance: float = 0.20
    weight_financial: float = 0.15

    # Monitoring thresholds (days)
    cert_alert_days_critical: int = 7
    cert_alert_days_high: int = 30
    cert_alert_days_medium: int = 60
    contract_alert_days: int = 60
    assessment_overdue_days: int = 365  # 12 months

    @property
    def weights_valid(self) -> bool:
        total = (
            self.weight_breach + self.weight_access
            + self.weight_compliance + self.weight_financial
        )
        return abs(total - 1.0) < 1e-6


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings singleton. Use this in FastAPI Depends()."""
    return Settings()
