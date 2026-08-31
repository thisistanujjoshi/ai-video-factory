from datetime import datetime

from pydantic import BaseModel


class MetricOut(BaseModel):
    id: int
    publication_id: int
    platform: str
    snapshot_label: str
    collected_at: datetime
    views: int
    likes: int
    comments: int
    shares: int
    watch_time_seconds: float | None
    retention_rate: float | None
    followers_gained: int
    engagement_rate: float

    @classmethod
    def from_metric(cls, metric) -> "MetricOut":
        return cls(
            id=metric.id,
            publication_id=metric.publication_id,
            platform=metric.publication.platform,
            snapshot_label=metric.snapshot_label,
            collected_at=metric.collected_at,
            views=metric.views,
            likes=metric.likes,
            comments=metric.comments,
            shares=metric.shares,
            watch_time_seconds=metric.watch_time_seconds,
            retention_rate=metric.retention_rate,
            followers_gained=metric.followers_gained,
            engagement_rate=metric.engagement_rate,
        )


class VideoAnalyticsOut(BaseModel):
    video_id: int
    title: str | None
    metrics: list[MetricOut]
    totals: dict
