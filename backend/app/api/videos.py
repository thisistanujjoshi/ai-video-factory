from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.storyboard import StoryboardAgent
from app.database import get_db
from app.models import ContentProfile, Idea, Publication, Script, Video, VideoState, transition
from app.providers.llm import get_llm_provider
from app.schemas.analytics import MetricOut
from app.schemas.publication import PublicationOut, ScheduleRequest
from app.schemas.qa import QAReportOut
from app.schemas.video import VideoOut
from app.services.analytics import collect_metrics_for_video
from app.services.pipeline import generate_video_from_idea
from app.services.production import produce_video
from app.services.publishing import publish_video, schedule_video
from app.services.qa import run_qa

router = APIRouter(prefix="/videos", tags=["videos"])


def _require_state(video: Video, expected: VideoState) -> None:
    if video.state != expected:
        raise HTTPException(
            status_code=409,
            detail=f"video is in state {video.state.value}, expected {expected.value}",
        )


def _require_state_in(video: Video, expected: set[VideoState]) -> None:
    if video.state not in expected:
        names = ", ".join(s.value for s in expected)
        raise HTTPException(
            status_code=409,
            detail=f"video is in state {video.state.value}, expected one of {names}",
        )


def _get_script_and_profile(db: Session, video: Video) -> tuple[Script, ContentProfile]:
    script = db.get(Script, video.script_id)
    profile = db.get(ContentProfile, video.content_profile_id)
    if script is None or profile is None:
        raise HTTPException(status_code=404, detail="script or content profile not found")
    return script, profile


class VideoGenerateRequest(BaseModel):
    idea_id: int


@router.post("/generate", response_model=VideoOut, status_code=201)
async def generate_video(payload: VideoGenerateRequest, db: Session = Depends(get_db)) -> Video:
    idea = db.get(Idea, payload.idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="idea not found")
    profile = db.get(ContentProfile, idea.content_profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="content profile not found")

    return await generate_video_from_idea(db, idea, profile)


@router.post("/{video_id}/render", response_model=VideoOut)
async def render_video_endpoint(video_id: int, db: Session = Depends(get_db)) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    _require_state(video, VideoState.STORYBOARD_READY)
    profile = db.get(ContentProfile, video.content_profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="content profile not found")

    await produce_video(db, video, profile)
    db.refresh(video)
    return video


@router.post("/{video_id}/qa", response_model=QAReportOut)
async def qa_video(video_id: int, db: Session = Depends(get_db)) -> QAReportOut:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    _require_state(video, VideoState.RENDERED)
    script, profile = _get_script_and_profile(db, video)

    outcome = await run_qa(db, video, script, profile)
    return QAReportOut(
        video=VideoOut.model_validate(video),
        passed=outcome.passed,
        technical_issues=outcome.technical.issues,
        content_score=outcome.content.score,
        content_approved=outcome.content.approved,
        content_issues=outcome.content.issues,
        content_recommendations=outcome.content.recommendations,
    )


@router.post("/{video_id}/regenerate", response_model=VideoOut)
async def regenerate_video(video_id: int, db: Session = Depends(get_db)) -> Video:
    """Full-video regeneration: a fresh storyboard, back to storyboard_ready
    (call /render and /qa again from there).

    ponytail: whole-storyboard regen, not per-scene. Section 23 explicitly
    wants "don't regenerate the whole video for one bad scene" as the
    eventual behavior; that needs partial re-render plumbing this MVP
    doesn't have yet (same gap noted in Phase 2's BUILD_STATUS). Add a
    scene-scoped variant once QA can point at which scene actually failed.
    """
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    _require_state(video, VideoState.QA_FAILED)
    script, profile = _get_script_and_profile(db, video)

    transition(video, VideoState.STORYBOARD_GENERATING)
    video.scenes.clear()
    await StoryboardAgent(get_llm_provider()).generate(db, script, profile, video)
    transition(video, VideoState.STORYBOARD_READY)

    db.commit()
    db.refresh(video)
    return video


@router.post("/{video_id}/approve", response_model=VideoOut)
def approve_video(video_id: int, db: Session = Depends(get_db)) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    _require_state(video, VideoState.AWAITING_APPROVAL)
    transition(video, VideoState.APPROVED)
    db.commit()
    db.refresh(video)
    return video


@router.post("/{video_id}/reject", response_model=VideoOut)
def reject_video(video_id: int, db: Session = Depends(get_db)) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    _require_state(video, VideoState.AWAITING_APPROVAL)
    transition(video, VideoState.REJECTED)
    db.commit()
    db.refresh(video)
    return video


@router.post("/{video_id}/schedule", response_model=list[PublicationOut])
async def schedule_video_endpoint(
    video_id: int, payload: ScheduleRequest, db: Session = Depends(get_db)
) -> list[Publication]:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    _require_state(video, VideoState.APPROVED)
    script, profile = _get_script_and_profile(db, video)

    return await schedule_video(db, video, profile, script, payload.scheduled_for)


@router.post("/{video_id}/publish", response_model=list[PublicationOut])
async def publish_video_endpoint(video_id: int, db: Session = Depends(get_db)) -> list[Publication]:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    _require_state_in(video, {VideoState.APPROVED, VideoState.SCHEDULED})
    script, profile = _get_script_and_profile(db, video)

    return await publish_video(db, video, profile, script)


@router.get("/{video_id}/publications", response_model=list[PublicationOut])
def list_publications(video_id: int, db: Session = Depends(get_db)) -> list[Publication]:
    return db.query(Publication).filter_by(video_id=video_id).order_by(Publication.platform).all()


@router.post("/{video_id}/analytics/collect", response_model=list[MetricOut])
async def collect_analytics(
    video_id: int, snapshot_label: str = "manual", db: Session = Depends(get_db)
) -> list[MetricOut]:
    """Collect one snapshot now for every PUBLISHED platform on this video.

    ponytail: caller-supplied label, triggered on demand -- no Celery beat
    scheduler wired up to fire this automatically at 1h/6h/24h/48h/7d
    (spec section 34) yet. Add that once there's a real job scheduler
    (same gap noted for the rest of the pipeline); an external cron/script
    calling this endpoint with the right label works in the meantime.
    """
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    metrics = await collect_metrics_for_video(db, video_id, snapshot_label)
    return [MetricOut.from_metric(m) for m in metrics]


@router.get("", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db)) -> list[Video]:
    return db.query(Video).order_by(Video.id.desc()).all()


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    return video


@router.get("/{video_id}/file")
def get_video_file(video_id: int, db: Session = Depends(get_db)) -> FileResponse:
    video = db.get(Video, video_id)
    if video is None or not video.rendered_path:
        raise HTTPException(status_code=404, detail="rendered video not found")
    return FileResponse(video.rendered_path, media_type="video/mp4")
