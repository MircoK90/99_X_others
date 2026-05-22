from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    postgres_user: str = "pipeline"
    postgres_password: str = "pipeline"
    postgres_db: str = "social_pipeline"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "social-pipeline/0.1"

    # Bluesky
    bluesky_handle: str = ""
    bluesky_app_password: str = ""

    # YouTube
    youtube_api_key: str = ""

    # Apify
    apify_api_token: str = ""

    # App
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
