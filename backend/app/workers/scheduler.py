import asyncio
import logging

from app.database.session import SessionLocal
from app.models import ContentProfile
from app.services.autonomous import (
    AutomationDisabledError,
    NoViableIdeasError,
    run_autonomous_cycle,
)
from app.services.scheduler import profiles_due_for_cycle
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="scheduler.run_profile_cycle")
def run_profile_cycle(profile_id: int) -> str:
    """Runs one autonomous cycle for a single profile, as its own Celery
    task so profiles due at the same beat tick run as independent,
    parallel tasks instead of serially inside one long task.

    A scheduled cycle is unattended: AutomationDisabledError (mode
    flipped to manual after this was enqueued) and NoViableIdeasError
    (spec section 37 dedup rejected everything this cycle) are expected,
    logged, and swallowed rather than raised -- there's no human here to
    see a Celery retry/failure, and raising would just get retried into
    the same outcome every time.
    """
    db = SessionLocal()
    try:
        profile = db.get(ContentProfile, profile_id)
        if profile is None:
            return f"profile {profile_id} no longer exists"
        try:
            asyncio.run(run_autonomous_cycle(db, profile))
        except (AutomationDisabledError, NoViableIdeasError) as exc:
            logger.info("scheduled cycle skipped for profile %s: %s", profile_id, exc)
            return str(exc)
        return f"profile {profile_id} cycle complete"
    finally:
        db.close()


@celery_app.task(name="scheduler.check_schedules")
def check_schedules() -> list[int]:
    """Beat-triggered every SCHEDULER_INTERVAL_SECONDS (see celery_app.py):
    find profiles under today's videos_per_day quota and enqueue one
    run_profile_cycle task per profile. Returns the profile IDs enqueued,
    mainly so tests and manual `celery call` invocations can see what it
    decided to do.
    """
    db = SessionLocal()
    try:
        due = profiles_due_for_cycle(db)
        for profile in due:
            run_profile_cycle.delay(profile.id)
        return [p.id for p in due]
    finally:
        db.close()
