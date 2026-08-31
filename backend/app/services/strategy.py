from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import ContentProfile, Idea, Script, Video, VideoState
from app.services.analytics import latest_metrics_for_video

# ponytail: no "hook_type" column exists on Idea (the LLM freely writes a
# hook, it isn't tagged from profile.strategy.hook_types) -- target_emotion
# is the closest stored categorical stand-in for "what kind of hook worked."


def _duration_bucket(seconds: float, profile: ContentProfile) -> str:
    min_d = profile.video.get("min_duration_seconds", 0)
    max_d = profile.video.get("max_duration_seconds", min_d + 1)
    span = max(max_d - min_d, 1)
    fraction = (seconds - min_d) / span
    if fraction < 1 / 3:
        return "short"
    if fraction < 2 / 3:
        return "medium"
    return "long"


def _bucket_stats(rows: list[tuple[str, float, float]]) -> dict:
    """rows: (bucket_key, engagement_rate, retention_rate) -- averages
    each, with the sample size every bucket carries so a consumer can
    judge how much to trust it (spec section 35: correlation, not
    causation, and small samples are exactly where that caveat matters)."""
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for key, engagement, retention in rows:
        grouped[key].append((engagement, retention))

    return {
        key: {
            "avg_engagement_rate": round(sum(e for e, _ in values) / len(values), 4),
            "avg_retention_rate": round(sum(r for _, r in values) / len(values), 4),
            "sample_size": len(values),
        }
        for key, values in grouped.items()
    }


def compute_patterns(db: Session, content_profile_id: int) -> dict:
    """Pure aggregation, no LLM -- the StrategyAgent reasons over this,
    it doesn't compute it (Rule 4)."""
    profile = db.get(ContentProfile, content_profile_id)
    if profile is None:
        raise ValueError(f"content profile {content_profile_id} not found")
    videos = (
        db.query(Video)
        .filter_by(content_profile_id=content_profile_id, state=VideoState.PUBLISHED)
        .all()
    )

    by_emotion: list[tuple[str, float, float]] = []
    by_duration: list[tuple[str, float, float]] = []
    by_platform: list[tuple[str, float, float]] = []
    titles_by_engagement: list[tuple[str, float]] = []

    for video in videos:
        metrics = latest_metrics_for_video(db, video.id)
        if not metrics:
            continue
        avg_engagement = sum(m.engagement_rate for m in metrics) / len(metrics)
        avg_retention = sum(m.retention_rate or 0 for m in metrics) / len(metrics)

        idea = db.get(Idea, video.idea_id) if video.idea_id else None
        script = db.get(Script, video.script_id) if video.script_id else None
        if idea:
            by_emotion.append((idea.target_emotion, avg_engagement, avg_retention))
            titles_by_engagement.append((idea.title, avg_engagement))
        if script:
            bucket = _duration_bucket(script.estimated_duration_seconds, profile)
            by_duration.append((bucket, avg_engagement, avg_retention))
        for metric in metrics:
            by_platform.append(
                (metric.publication.platform, metric.engagement_rate, metric.retention_rate or 0)
            )

    top_titles = [title for title, _ in sorted(titles_by_engagement, key=lambda t: -t[1])[:5]]

    return {
        "sample_size": len(videos),
        "by_target_emotion": _bucket_stats(by_emotion),
        "by_duration_bucket": _bucket_stats(by_duration),
        "by_platform": _bucket_stats(by_platform),
        "top_performing_titles": top_titles,
    }
