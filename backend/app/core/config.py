from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bounty Pool"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+pysqlite:///./bounty_pool.db"
    cors_origins: str = "http://localhost:3000"
    bounty_pool_intelligence_llm_enabled: bool = True
    bounty_pool_zhipu_api_key: str | None = None
    bounty_pool_zhipu_model: str = "glm-4-flash-250414"
    bounty_pool_zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
