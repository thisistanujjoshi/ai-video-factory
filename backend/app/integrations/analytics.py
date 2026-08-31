import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawMetrics:
    views: int
    likes: int
    comments: int
    shares: int
    watch_time_seconds: float | None
    retention_rate: float | None
    followers_gained: int
    raw: dict = field(default_factory=dict)


class AnalyticsCollector(ABC):
    """One implementation per platform, called with a Publication (needs
    its `platform_ref` — the platform's own video/media id)."""

    @abstractmethod
    async def collect(self, publication) -> RawMetrics: ...


class MockAnalyticsCollector(AnalyticsCollector):
    """Plausible, deterministic-per-publication fake numbers -- no
    platform API, no OAuth. Seeded by publication id so repeated
    collection calls in a test are reproducible (a real collector's
    numbers would naturally change between calls)."""

    def __init__(self, platform: str):
        self.platform = platform

    async def collect(self, publication) -> RawMetrics:
        rng = random.Random(f"{publication.platform}:{publication.id}")
        views = rng.randint(500, 50_000)
        likes = int(views * rng.uniform(0.02, 0.12))
        comments = int(views * rng.uniform(0.001, 0.01))
        shares = int(views * rng.uniform(0.001, 0.02))
        watch_time = round(views * rng.uniform(15, 45), 1)
        retention = round(rng.uniform(0.3, 0.85), 3)
        followers = rng.randint(0, int(views * 0.01))
        return RawMetrics(
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            watch_time_seconds=watch_time,
            retention_rate=retention,
            followers_gained=followers,
            raw={"mock": True, "platform": publication.platform},
        )


class YouTubeAnalyticsCollector(AnalyticsCollector):
    """YouTube Analytics API v2 `reports.query` (views/likes/comments/
    shares/averageViewDuration/subscribersGained), scoped by video id.
    NOT IMPLEMENTED — same OAuth gap as YouTubePublisher."""

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token

    async def collect(self, publication) -> RawMetrics:
        raise NotImplementedError("YouTube Analytics needs the same OAuth flow as YouTubePublisher")


class InstagramInsightsCollector(AnalyticsCollector):
    """Instagram Graph API `/{media-id}/insights` (reach, likes, comments,
    shares, saves for a Reel). NOT IMPLEMENTED — same OAuth gap as
    InstagramPublisher."""

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token

    async def collect(self, publication) -> RawMetrics:
        raise NotImplementedError(
            "Instagram Insights needs the same Page access token as InstagramPublisher"
        )


class TikTokAnalyticsCollector(AnalyticsCollector):
    """TikTok Display/Research API video query (view_count, like_count,
    comment_count, share_count). NOT IMPLEMENTED — same OAuth gap as
    TikTokPublisher."""

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token

    async def collect(self, publication) -> RawMetrics:
        raise NotImplementedError(
            "TikTok Analytics needs the same OAuth access token as TikTokPublisher"
        )


def get_analytics_collector(platform: str) -> AnalyticsCollector:
    """Real collectors exist (see docstrings) but need the same OAuth
    flows as their Publisher counterparts -- mock stands in until then."""
    return MockAnalyticsCollector(platform)
