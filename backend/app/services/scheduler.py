from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models import AutomationMode, ContentProfile, Video


def _as_utc_date(dt: datetime) -> date:
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    return dt.date()


def videos_needed_today(db: Session, profile: ContentProfile, now: datetime) -> int:
    """How many more videos this profile should attempt today to hit its
    schedule.videos_per_day quota. Counts videos in any state (including
    qa_failed/rejected) -- a failed attempt still used up today's
    production slot; the point is bounding attempts per day, not
    immediately retrying failures.

    ponytail: "today" is a fixed UTC day, not the profile's own timezone
    -- schedule has no timezone field yet (spec's posting_windows/
    timezone belong to the publishing scheduler, not this one). Add a
    schedule.timezone field and use it here if profiles ever need
    midnight-local resets instead of midnight-UTC.
    """
    quota = (profile.schedule or {}).get("videos_per_day", 1)
    today = _as_utc_date(now)
    produced_today = sum(
        1
        for (created_at,) in db.query(Video.created_at).filter(
            Video.content_profile_id == profile.id
        )
        if _as_utc_date(created_at) == today
    )
    return max(0, quota - produced_today)


def profiles_due_for_cycle(db: Session, now: datetime | None = None) -> list[ContentProfile]:
    """Non-manual profiles that haven't hit today's videos_per_day quota yet."""
    now = now or datetime.now(UTC)
    profiles = (
        db.query(ContentProfile)
        .filter(ContentProfile.automation_mode != AutomationMode.MANUAL)
        .all()
    )
    return [p for p in profiles if videos_needed_today(db, p, now) > 0]
