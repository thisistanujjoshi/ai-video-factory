from app.models import (
    ContentProfile,
    Idea,
    Metric,
    Publication,
    PublicationStatus,
    Script,
    Video,
    VideoState,
)
from app.services.strategy import compute_patterns


def _profile(db_session) -> ContentProfile:
    profile = ContentProfile(
        name="Strategy Test",
        niche={"primary": "mystery", "secondary": []},
        audience={"min_age": 18, "max_age": 35, "language": "English"},
        video={
            "type": "short",
            "min_duration_seconds": 30,
            "max_duration_seconds": 90,
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
        publishing={"youtube": True},
        schedule={"videos_per_day": 1},
    )
    db_session.add(profile)
    db_session.flush()
    return profile


def _add_published_video(
    db_session, profile, *, title, emotion, duration_seconds, engagement_rate, retention_rate
):
    idea = Idea(
        content_profile_id=profile.id,
        title=title,
        premise="p",
        hook="h",
        target_emotion=emotion,
        format="narrated",
        estimated_duration=60,
        difficulty="medium",
        scores={},
        overall_score=80.0,
    )
    db_session.add(idea)
    db_session.flush()
    script = Script(
        idea_id=idea.id,
        title=title,
        hook="h",
        narration="n",
        estimated_duration_seconds=duration_seconds,
        cta="c",
        engagement_question="?",
        scenes=[],
    )
    db_session.add(script)
    db_session.flush()
    video = Video(
        content_profile_id=profile.id,
        idea_id=idea.id,
        script_id=script.id,
        state=VideoState.PUBLISHED,
        title=title,
    )
    db_session.add(video)
    db_session.flush()
    publication = Publication(
        video_id=video.id,
        platform="youtube",
        status=PublicationStatus.PUBLISHED,
        platform_metadata={},
    )
    db_session.add(publication)
    db_session.flush()
    views = 1000
    db_session.add(
        Metric(
            publication_id=publication.id,
            snapshot_label="manual",
            views=views,
            likes=int(views * engagement_rate),
            comments=0,
            shares=0,
            retention_rate=retention_rate,
            engagement_rate=engagement_rate,
        )
    )
    db_session.flush()
    return video


def test_compute_patterns_aggregates_by_emotion_and_duration(db_session):
    profile = _profile(db_session)
    # min=30, max=90 -> span 60: short < 50s, medium 50-70s, long > 70s
    _add_published_video(
        db_session,
        profile,
        title="A",
        emotion="fear",
        duration_seconds=40,
        engagement_rate=0.10,
        retention_rate=0.8,
    )
    _add_published_video(
        db_session,
        profile,
        title="B",
        emotion="fear",
        duration_seconds=45,
        engagement_rate=0.06,
        retention_rate=0.4,
    )
    _add_published_video(
        db_session,
        profile,
        title="C",
        emotion="curiosity",
        duration_seconds=85,
        engagement_rate=0.02,
        retention_rate=0.2,
    )

    patterns = compute_patterns(db_session, profile.id)

    assert patterns["sample_size"] == 3
    assert patterns["by_target_emotion"]["fear"]["sample_size"] == 2
    assert patterns["by_target_emotion"]["fear"]["avg_engagement_rate"] == 0.08
    assert patterns["by_target_emotion"]["curiosity"]["sample_size"] == 1
    assert patterns["by_duration_bucket"]["short"]["sample_size"] == 2
    assert patterns["by_duration_bucket"]["long"]["sample_size"] == 1
    assert patterns["top_performing_titles"][0] == "A"  # highest engagement first


def test_compute_patterns_with_no_history_returns_empty_buckets(db_session):
    profile = _profile(db_session)
    patterns = compute_patterns(db_session, profile.id)
    assert patterns == {
        "sample_size": 0,
        "by_target_emotion": {},
        "by_duration_bucket": {},
        "by_platform": {},
        "top_performing_titles": [],
    }
