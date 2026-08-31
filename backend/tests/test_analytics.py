import pytest

from app.integrations.analytics import (
    InstagramInsightsCollector,
    MockAnalyticsCollector,
    TikTokAnalyticsCollector,
    YouTubeAnalyticsCollector,
)
from app.models import ContentProfile, Publication, PublicationStatus, Video, VideoState
from app.services.analytics import collect_metrics_for_video, latest_metrics_for_video, sum_totals


def _make_published_video(db_session, platforms: list[str]) -> Video:
    profile = ContentProfile(
        name="Analytics Test",
        niche={"primary": "mystery", "secondary": []},
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
        publishing={p: True for p in platforms},
        schedule={"videos_per_day": 1},
    )
    db_session.add(profile)
    db_session.flush()
    video = Video(content_profile_id=profile.id, state=VideoState.PUBLISHED, title="Test Video")
    db_session.add(video)
    db_session.flush()
    for platform in platforms:
        db_session.add(
            Publication(
                video_id=video.id,
                platform=platform,
                status=PublicationStatus.PUBLISHED,
                platform_metadata={},
                platform_ref=f"mock-{platform}-{video.id}",
            )
        )
    db_session.flush()
    return video


class _FakePublication:
    def __init__(self, publication_id: int, platform: str):
        self.id = publication_id
        self.platform = platform


async def test_mock_collector_returns_plausible_deterministic_metrics():
    collector = MockAnalyticsCollector("youtube")
    pub = _FakePublication(1, "youtube")

    first = await collector.collect(pub)
    second = await collector.collect(pub)

    assert first.views > 0
    assert first.views == second.views  # deterministic given the same publication
    assert 0 <= first.retention_rate <= 1


async def test_collect_metrics_for_video_creates_one_metric_per_published_platform(db_session):
    video = _make_published_video(db_session, ["youtube", "instagram"])

    metrics = await collect_metrics_for_video(db_session, video.id, snapshot_label="1h")

    assert len(metrics) == 2
    assert all(m.snapshot_label == "1h" for m in metrics)
    assert all(m.views > 0 for m in metrics)
    assert all(0 <= m.engagement_rate for m in metrics)


async def test_collect_metrics_skips_unpublished_platforms(db_session):
    video = _make_published_video(db_session, ["youtube"])
    video.state = VideoState.SCHEDULED
    pending = Publication(
        video_id=video.id, platform="tiktok", status=PublicationStatus.PENDING, platform_metadata={}
    )
    db_session.add(pending)
    db_session.flush()

    metrics = await collect_metrics_for_video(db_session, video.id)

    assert len(metrics) == 1  # only the published youtube publication


async def test_latest_metrics_returns_most_recent_snapshot_per_publication(db_session):
    video = _make_published_video(db_session, ["youtube"])

    await collect_metrics_for_video(db_session, video.id, snapshot_label="1h")
    await collect_metrics_for_video(db_session, video.id, snapshot_label="6h")

    latest = latest_metrics_for_video(db_session, video.id)
    assert len(latest) == 1
    assert latest[0].snapshot_label == "6h"


def test_sum_totals():
    from app.models import Metric

    metrics = [
        Metric(views=100, likes=10, comments=2, shares=1, followers_gained=5),
        Metric(views=200, likes=20, comments=4, shares=2, followers_gained=3),
    ]
    totals = sum_totals(metrics)
    assert totals == {"views": 300, "likes": 30, "comments": 6, "shares": 3, "followers_gained": 8}


@pytest.mark.parametrize(
    "collector_cls",
    [YouTubeAnalyticsCollector, InstagramInsightsCollector, TikTokAnalyticsCollector],
)
async def test_real_collectors_are_not_implemented_yet(collector_cls):
    collector = collector_cls()
    with pytest.raises(NotImplementedError):
        await collector.collect(_FakePublication(1, "x"))
