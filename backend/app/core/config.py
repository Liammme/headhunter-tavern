from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SQLITE_PATH = (Path(__file__).resolve().parents[2] / "bounty_pool.db").as_posix()


class Settings(BaseSettings):
    app_name: str = "Bounty Pool"
    api_prefix: str = "/api/v1"
    database_url: str = f"sqlite+pysqlite:///{DEFAULT_SQLITE_PATH}"
    cors_origins: str = "http://localhost:3000"
    bounty_pool_intelligence_llm_enabled: bool = True
    bounty_pool_zhipu_api_key: str | None = None
    bounty_pool_zhipu_model: str = "glm-4-flash-250414"
    bounty_pool_zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    bounty_pool_zhipu_fallback_models: str = "glm-4-flash-250414,glm-4.7-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def parse_cors_origins(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
