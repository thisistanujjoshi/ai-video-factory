from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.scripts import ScriptAgent
from app.agents.storyboard import StoryboardAgent
from app.database import get_db
from app.models import ContentProfile, Idea, Script, Video, VideoState, transition
from app.providers.llm import get_llm_provider
from app.schemas.qa import QAReportOut
from app.schemas.video import VideoOut
from app.services.production import produce_video
from app.services.qa import run_qa

router = APIRouter(prefix="/videos", tags=["videos"])


def _require_state(video: Video, expected: VideoState) -> None:
    if video.state != expected:
        raise HTTPException(
            status_code=409,
            detail=f"video is in state {video.state.value}, expected {expected.value}",
        )


class VideoGenerateRequest(BaseModel):
    idea_id: int


@router.post("/generate", response_model=VideoOut, status_code=201)
async def generate_video(payload: VideoGenerateRequest, db: Session = Depends(get_db)) -> Video:
    """Idea -> script -> storyboard, synchronously.

    ponytail: no Celery job here yet -- the mock LLM is instant, so a
    request/response round trip is the whole pipeline. Move this behind a
    job when Phase 2 adds asset generation/rendering, which actually takes
    real time and benefits from being async + parallel per scene.
    """
    idea = db.get(Idea, payload.idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="idea not found")
    profile = db.get(ContentProfile, idea.content_profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="content profile not found")

    llm = get_llm_provider()

    video = Video(
        content_profile_id=profile.id, idea_id=idea.id, state=VideoState.DRAFT, title=idea.title
    )
    db.add(video)
    db.flush()

    transition(video, VideoState.IDEA_SELECTED)

    transition(video, VideoState.SCRIPT_GENERATING)
    script = await ScriptAgent(llm).generate(db, idea, profile)
    video.script_id = script.id
    transition(video, VideoState.SCRIPT_READY)

    transition(video, VideoState.STORYBOARD_GENERATING)
    await StoryboardAgent(llm).generate(db, script, profile, video)
    transition(video, VideoState.STORYBOARD_READY)

    db.commit()
    db.refresh(video)
    return video


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
    script = db.get(Script, video.script_id)
    profile = db.get(ContentProfile, video.content_profile_id)
    if script is None or profile is None:
        raise HTTPException(status_code=404, detail="script or content profile not found")

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
    script = db.get(Script, video.script_id)
    profile = db.get(ContentProfile, video.content_profile_id)
    if script is None or profile is None:
        raise HTTPException(status_code=404, detail="script or content profile not found")

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
