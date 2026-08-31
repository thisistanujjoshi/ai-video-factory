import asyncio
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.integrations import PLATFORMS, PublishError, get_publisher
from app.models import (
    ContentProfile,
    Publication,
    PublicationStatus,
    Script,
    Video,
    VideoState,
    transition,
)

MAX_PUBLISH_RETRIES = 3
# ponytail: real backoff would be seconds (1s/2s/4s...); shortened so tests
# stay fast. This is still a real sleep-based retry loop, not a fake one.
RETRY_BASE_DELAY_SECONDS = 0.05


def build_platform_metadata(platform: str, script: Script, profile: ContentProfile) -> dict:
    """Deterministic, not LLM-generated -- it's just packaging content the
    idea/script agents already produced into each platform's shape (spec
    section 31). Nothing here requires judgment an LLM call would add;
    revisit if per-platform hook framing turns out to matter."""
    hashtags = [
        f"#{tag.replace(' ', '')}"
        for tag in [profile.niche.get("primary", ""), *profile.niche.get("secondary", [])]
        if tag
    ]

    if platform == "youtube":
        return {
            "title": script.title[:100],
            "description": f"{script.narration}\n\n{script.cta}",
            "tags": [profile.niche.get("primary", ""), *profile.niche.get("secondary", [])],
        }
    # instagram and tiktok share a caption+hashtags shape
    return {
        "caption": f"{script.hook}\n\n{script.cta}",
        "hashtags": hashtags,
    }


async def _publish_with_retry(publisher, video: Video, publication: Publication) -> None:
    last_error: Exception | None = None
    for attempt in range(MAX_PUBLISH_RETRIES):
        try:
            result = await publisher.publish(video, publication.platform_metadata)
            publication.status = result.status
            publication.platform_ref = result.platform_ref
            publication.published_at = datetime.now(UTC)
            publication.error = None
            return
        except PublishError as exc:
            last_error = exc
            publication.retry_count += 1
            if attempt < MAX_PUBLISH_RETRIES - 1:
                await asyncio.sleep(RETRY_BASE_DELAY_SECONDS * (2**attempt))

    publication.status = PublicationStatus.FAILED
    publication.error = str(last_error)


async def publish_video(
    db: Session, video: Video, profile: ContentProfile, script: Script
) -> list[Publication]:
    """Approved/scheduled video -> attempt every platform enabled on the
    profile. Idempotent: a platform already PUBLISHED is left alone rather
    than re-published (spec section 58)."""
    transition(video, VideoState.PUBLISHING)
    db.flush()

    results: list[Publication] = []
    any_failed = False

    for platform in PLATFORMS:
        if not profile.publishing.get(platform, False):
            continue

        publication = (
            db.query(Publication).filter_by(video_id=video.id, platform=platform).one_or_none()
        )
        metadata = build_platform_metadata(platform, script, profile)
        if publication is None:
            publication = Publication(
                video_id=video.id, platform=platform, platform_metadata=metadata
            )
            db.add(publication)
            db.flush()
        elif publication.status == PublicationStatus.PUBLISHED:
            results.append(publication)
            continue
        else:
            publication.platform_metadata = metadata

        publication.status = PublicationStatus.PUBLISHING
        await _publish_with_retry(get_publisher(platform), video, publication)
        if publication.status != PublicationStatus.PUBLISHED:
            any_failed = True
        results.append(publication)

    transition(video, VideoState.FAILED if any_failed else VideoState.PUBLISHED)
    db.commit()
    for publication in results:
        db.refresh(publication)
    return results


async def schedule_video(
    db: Session, video: Video, profile: ContentProfile, script: Script, when: datetime
) -> list[Publication]:
    transition(video, VideoState.SCHEDULED)

    results: list[Publication] = []
    for platform in PLATFORMS:
        if not profile.publishing.get(platform, False):
            continue
        metadata = build_platform_metadata(platform, script, profile)
        publication = (
            db.query(Publication).filter_by(video_id=video.id, platform=platform).one_or_none()
        )
        if publication is None:
            publication = Publication(
                video_id=video.id, platform=platform, platform_metadata=metadata
            )
            db.add(publication)
        else:
            publication.platform_metadata = metadata
        publication.status = PublicationStatus.SCHEDULED
        publication.scheduled_for = when
        results.append(publication)

    db.commit()
    for publication in results:
        db.refresh(publication)
    return results
