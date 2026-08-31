from app.config import get_settings


def test_settings_load_with_defaults():
    settings = get_settings()
    assert settings.app_env
    assert settings.database_url.startswith("postgresql")
    assert settings.redis_url.startswith("redis")
