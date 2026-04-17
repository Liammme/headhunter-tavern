from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bounty Pool"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+pysqlite:///./bounty_pool.db"
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
