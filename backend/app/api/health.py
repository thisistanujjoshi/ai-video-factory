from fastapi import APIRouter
from redis import Redis
from sqlalchemy import text

from app.config import get_settings
from app.database import engine

router = APIRouter()


@router.get("/health")
def health() -> dict:
    settings = get_settings()

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception as exc:  # noqa: BLE001 - report any connectivity failure, not a specific type
        database = f"error: {exc}"

    try:
        Redis.from_url(settings.redis_url, socket_connect_timeout=2).ping()
        redis_status = "ok"
    except Exception as exc:  # noqa: BLE001
        redis_status = f"error: {exc}"

    return {
        "status": "ok" if database == "ok" and redis_status == "ok" else "degraded",
        "app_env": settings.app_env,
        "database": database,
        "redis": redis_status,
    }
