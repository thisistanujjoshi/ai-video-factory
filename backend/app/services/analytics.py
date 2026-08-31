from sqlalchemy.orm import Session

from app.integrations import get_analytics_collector
from app.models import Metric, Publication, PublicationStatus


async def collect_metrics_for_video(
    db: Session, video_id: int, snapshot_label: str = "manual"
) -> list[Metric]:
    """One snapshot per PUBLISHED platform. Doesn't touch unpublished/
    failed publications -- nothing to measure yet."""
    publications = (
        db.query(Publication).filter_by(video_id=video_id, status=PublicationStatus.PUBLISHED).all()
    )

    metrics = []
    for publication in publications:
        raw = await get_analytics_collector(publication.platform).collect(publication)
        engagement_rate = (raw.likes + raw.comments + raw.shares) / raw.views if raw.views else 0.0
        metric = Metric(
            publication_id=publication.id,
            snapshot_label=snapshot_label,
            views=raw.views,
            likes=raw.likes,
            comments=raw.comments,
            shares=raw.shares,
            watch_time_seconds=raw.watch_time_seconds,
            retention_rate=raw.retention_rate,
            followers_gained=raw.followers_gained,
            engagement_rate=round(engagement_rate, 4),
            raw=raw.raw,
        )
        db.add(metric)
        metrics.append(metric)

    db.commit()
    for metric in metrics:
        db.refresh(metric)
    return metrics


def latest_metrics_for_video(db: Session, video_id: int) -> list[Metric]:
    """Most recent snapshot per publication -- not every historical row."""
    publication_ids = [p.id for p in db.query(Publication.id).filter_by(video_id=video_id)]
    if not publication_ids:
        return []

    latest: dict[int, Metric] = {}
    for metric in (
        db.query(Metric)
        .filter(Metric.publication_id.in_(publication_ids))
        .order_by(Metric.collected_at)
    ):
        latest[metric.publication_id] = metric  # last write per publication wins (ascending order)
    return list(latest.values())


def sum_totals(metrics: list[Metric]) -> dict:
    return {
        "views": sum(m.views for m in metrics),
        "likes": sum(m.likes for m in metrics),
        "comments": sum(m.comments for m in metrics),
        "shares": sum(m.shares for m in metrics),
        "followers_gained": sum(m.followers_gained for m in metrics),
    }
