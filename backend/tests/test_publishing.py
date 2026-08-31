import pytest

from app.integrations import MockPublisher
from app.integrations.instagram import InstagramPublisher
from app.integrations.tiktok import TikTokPublisher
from app.integrations.youtube import YouTubePublisher
from app.models import (
    ContentProfile,
    Idea,
    Publication,
    PublicationStatus,
    Script,
    Video,
    VideoState,
)
from app.services import publishing as publishing_service
from app.services.publishing import build_platform_metadata, publish_video, schedule_video


def _make_profile(**publishing_overrides) -> ContentProfile:
    return ContentProfile(
        name="Test Profile",
        niche={"primary": "mystery", "secondary": ["unexplained", "true crime"]},
        audience={"min_age": 18, "max_age": 35, "language": "English"},
        video={
            "type": "short",
            "min_duration_seconds": 30,
            "max_duration_seconds": 60,
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
        },
        style={
            "tone": "mysterious",
            "pacing": "fast",
            "narration": "dramatic",
            "visual_style": "cinematic",
        },
        strategy={"hook_types": ["curiosity"]},
        publishing={"youtube": True, "instagram": True, "tiktok": False, **publishing_overrides},
        schedule={"videos_per_day": 1},
    )


def _make_video_chain(db_session, profile):
    db_session.add(profile)
    db_session.flush()
    idea = Idea(
        content_profile_id=profile.id,
        title="A Case",
        premise="p",
        hook="h",
        target_emotion="curiosity",
        format="narrated",
        estimated_duration=60,
        difficulty="medium",
        scores={},
        overall_score=80.0,
    )
    script = Script(
        idea_id=0,
        title="A Mysterious Case",
        hook="hook line",
        narration="narration text",
        estimated_duration_seconds=45.0,
        cta="Follow for more.",
        engagement_question="?",
        scenes=[],
    )
    db_session.add(idea)
    db_session.flush()
    script.idea_id = idea.id
    db_session.add(script)
    db_session.flush()
    video = Video(
        content_profile_id=profile.id,
        idea_id=idea.id,
        script_id=script.id,
        state=VideoState.APPROVED,
        title=script.title,
    )
    db_session.add(video)
    db_session.flush()
    return video, script


def test_build_platform_metadata_shapes():
    profile = _make_profile()
    script = Script(
        idea_id=1,
        title="X" * 150,
        hook="hook",
        narration="narration",
        estimated_duration_seconds=10,
        cta="cta",
        engagement_question="?",
        scenes=[],
    )

    youtube = build_platform_metadata("youtube", script, profile)
    assert len(youtube["title"]) <= 100
    assert "cta" in youtube["description"]
    assert youtube["tags"] == ["mystery", "unexplained", "true crime"]

    instagram = build_platform_metadata("instagram", script, profile)
    assert "hook" in instagram["caption"]
    assert "#mystery" in instagram["hashtags"]


async def test_publish_video_creates_publications_for_enabled_platforms(db_session):
    profile = _make_profile()
    video, script = _make_video_chain(db_session, profile)

    results = await publish_video(db_session, video, profile, script)

    platforms = {p.platform for p in results}
    assert platforms == {"youtube", "instagram"}  # tiktok disabled on this profile
    for pub in results:
        assert pub.status == PublicationStatus.PUBLISHED
        assert pub.platform_ref
    assert video.state == VideoState.PUBLISHED


async def test_publish_is_idempotent(db_session):
    profile = _make_profile(instagram=False)  # youtube only, simpler to assert on
    video, script = _make_video_chain(db_session, profile)

    first = await publish_video(db_session, video, profile, script)
    first_ref = first[0].platform_ref

    # video is now PUBLISHED; re-approve to simulate a duplicate publish request
    video.state = VideoState.APPROVED
    second = await publish_video(db_session, video, profile, script)

    assert second[0].platform_ref == first_ref  # not republished
    count = db_session.query(Publication).filter_by(video_id=video.id, platform="youtube").count()
    assert count == 1  # no duplicate row


async def test_publish_retries_transient_failures_then_succeeds(db_session, monkeypatch):
    profile = _make_profile(instagram=False)
    video, script = _make_video_chain(db_session, profile)

    monkeypatch.setattr(
        publishing_service, "get_publisher", lambda platform: MockPublisher(platform, fail_times=2)
    )

    results = await publish_video(db_session, video, profile, script)

    assert results[0].status == PublicationStatus.PUBLISHED
    assert results[0].retry_count == 2


async def test_publish_marks_failed_after_exhausting_retries(db_session, monkeypatch):
    profile = _make_profile(instagram=False)
    video, script = _make_video_chain(db_session, profile)

    monkeypatch.setattr(
        publishing_service, "get_publisher", lambda platform: MockPublisher(platform, fail_times=99)
    )

    results = await publish_video(db_session, video, profile, script)

    assert results[0].status == PublicationStatus.FAILED
    assert results[0].error
    assert video.state == VideoState.FAILED


async def test_schedule_video_creates_scheduled_publications(db_session):
    profile = _make_profile()
    video, script = _make_video_chain(db_session, profile)

    from datetime import UTC, datetime, timedelta

    when = datetime.now(UTC) + timedelta(days=1)
    results = await schedule_video(db_session, video, profile, script, when)

    assert all(p.status == PublicationStatus.SCHEDULED for p in results)
    assert video.state == VideoState.SCHEDULED


@pytest.mark.parametrize("publisher_cls", [YouTubePublisher, InstagramPublisher, TikTokPublisher])
async def test_real_publishers_are_not_implemented_yet(publisher_cls):
    publisher = publisher_cls(client_id="x", client_secret="y")
    with pytest.raises(NotImplementedError):
        await publisher.publish(video=None, metadata={})
