from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app config. All values come from environment variables (.env in dev).

    Provider keys are optional here because Phase 0 doesn't call any provider yet —
    they're declared so later phases don't need to touch this file to add a var.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_video_factory"
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: str | None = None
    llm_api_key: str | None = None

    image_provider: str | None = None
    image_api_key: str | None = None

    video_provider: str | None = None
    video_api_key: str | None = None

    tts_provider: str | None = None
    tts_api_key: str | None = None

    # Not in the spec's original env var list (section 48) -- added when
    # content-memory similarity detection (section 37) needed a provider
    # slot, same pattern as the other four.
    embedding_provider: str | None = None
    embedding_api_key: str | None = None

    storage_provider: str = "local"

    youtube_client_id: str | None = None
    youtube_client_secret: str | None = None
    instagram_client_id: str | None = None
    instagram_client_secret: str | None = None
    tiktok_client_id: str | None = None
    tiktok_client_secret: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
