from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SQLITE_PATH = (Path(__file__).resolve().parents[2] / "bounty_pool.db").as_posix()


def normalize_database_url(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("postgres://"):
        return "postgresql+psycopg://" + normalized[len("postgres://") :]
    if normalized.startswith("postgresql://"):
        return "postgresql+psycopg://" + normalized[len("postgresql://") :]
    return normalized


class Settings(BaseSettings):
    app_name: str = "Bounty Pool"
    api_prefix: str = "/api/v1"
    database_url: str = f"sqlite+pysqlite:///{DEFAULT_SQLITE_PATH}"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    bounty_pool_estimated_bounty_live_write_enabled: bool = False
    bounty_pool_estimated_bounty_read_enabled: bool = False
    bounty_pool_estimated_bounty_startup_audit_enabled: bool = False
    bounty_pool_estimated_bounty_audit_window_days: int = 14
    bounty_pool_intelligence_llm_enabled: bool = True
    bounty_pool_zhipu_api_key: str | None = None
    bounty_pool_zhipu_model: str = "glm-4-flash-250414"
    bounty_pool_zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    bounty_pool_zhipu_fallback_models: str = "glm-4-flash-250414,glm-4.7-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url_field(cls, value: str) -> str:
        return normalize_database_url(value)


settings = Settings()


def parse_cors_origins(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
