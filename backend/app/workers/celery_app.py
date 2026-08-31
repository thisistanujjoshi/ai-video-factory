from celery import Celery  # type: ignore[import-untyped]

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_video_factory",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


@celery_app.task(name="ping")
def ping() -> str:
    return "pong"
