from datetime import UTC, datetime, timedelta

from app.models import AutomationMode, ContentProfile, Video, VideoState
from app.services.scheduler import profiles_due_for_cycle, videos_needed_today


def _make_profile(db, *, mode, videos_per_day=1, name="p"):
    profile = ContentProfile(
        name=name,
        niche={"primary": "x"},
        audience={"min_age": 18, "max_age": 35},
        video={},
        style={"tone": "x", "pacing": "x", "narration": "x", "visual_style": "x"},
        strategy={},
        publishing={},
        schedule={"videos_per_day": videos_per_day},
        automation_mode=mode,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _add_video(db, profile, *, created_at):
    video = Video(content_profile_id=profile.id, state=VideoState.DRAFT)
    db.add(video)
    db.commit()
    video.created_at = created_at
    db.commit()
    return video


def test_videos_needed_today_full_quota_when_no_videos(db_session):
    profile = _make_profile(db_session, mode=AutomationMode.AUTONOMOUS, videos_per_day=2)
    assert videos_needed_today(db_session, profile, datetime.now(UTC)) == 2


def test_videos_needed_today_ignores_videos_from_other_days(db_session):
    profile = _make_profile(db_session, mode=AutomationMode.AUTONOMOUS, videos_per_day=2)
    now = datetime.now(UTC)
    _add_video(db_session, profile, created_at=now - timedelta(days=1))
    assert videos_needed_today(db_session, profile, now) == 2


def test_videos_needed_today_counts_todays_videos(db_session):
    profile = _make_profile(db_session, mode=AutomationMode.AUTONOMOUS, videos_per_day=2)
    now = datetime.now(UTC)
    _add_video(db_session, profile, created_at=now)
    assert videos_needed_today(db_session, profile, now) == 1


def test_videos_needed_today_never_goes_negative(db_session):
    profile = _make_profile(db_session, mode=AutomationMode.AUTONOMOUS, videos_per_day=1)
    now = datetime.now(UTC)
    _add_video(db_session, profile, created_at=now)
    _add_video(db_session, profile, created_at=now)
    assert videos_needed_today(db_session, profile, now) == 0


def test_profiles_due_for_cycle_skips_manual(db_session):
    _make_profile(db_session, mode=AutomationMode.MANUAL, name="manual")
    auto = _make_profile(db_session, mode=AutomationMode.AUTONOMOUS, name="auto")
    due = profiles_due_for_cycle(db_session, datetime.now(UTC))
    assert [p.id for p in due] == [auto.id]


def test_profiles_due_for_cycle_includes_semi_automatic(db_session):
    semi = _make_profile(db_session, mode=AutomationMode.SEMI_AUTOMATIC)
    due = profiles_due_for_cycle(db_session, datetime.now(UTC))
    assert [p.id for p in due] == [semi.id]


def test_profiles_due_for_cycle_skips_quota_already_met(db_session):
    profile = _make_profile(db_session, mode=AutomationMode.AUTONOMOUS, videos_per_day=1)
    _add_video(db_session, profile, created_at=datetime.now(UTC))
    assert profiles_due_for_cycle(db_session, datetime.now(UTC)) == []


def test_check_schedules_enqueues_one_task_per_due_profile(db_session, monkeypatch):
    from app.workers import scheduler as scheduler_tasks

    monkeypatch.setattr(scheduler_tasks, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    profile = _make_profile(db_session, mode=AutomationMode.AUTONOMOUS)
    calls: list[int] = []
    monkeypatch.setattr(scheduler_tasks.run_profile_cycle, "delay", calls.append)

    result = scheduler_tasks.check_schedules()

    assert calls == [profile.id]
    assert result == [profile.id]
