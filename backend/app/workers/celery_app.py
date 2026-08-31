from celery import Celery  # type: ignore[import-untyped]

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_video_factory",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.scheduler"],
)

# Every 15 minutes: frequent enough that a fresh videos_per_day quota (a
# profile edited, or a new UTC day starting) gets picked up well within
# the hour, infrequent enough not to hammer the DB/LLM checking profiles
# that have nothing to do. See app.services.scheduler for the actual
# quota logic; this task just decides *when* to ask it.
celery_app.conf.beat_schedule = {
    "check-content-schedules": {
        "task": "scheduler.check_schedules",
        "schedule": 900.0,
    },
}


@celery_app.task(name="ping")
def ping() -> str:
    return "pong"
