from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.scripts import ScriptAgent
from app.agents.storyboard import StoryboardAgent
from app.database import get_db
from app.models import ContentProfile, Idea, Video, VideoState, transition
from app.providers.llm import get_llm_provider
from app.schemas.video import VideoOut

router = APIRouter(prefix="/videos", tags=["videos"])


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


@router.get("", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db)) -> list[Video]:
    return db.query(Video).order_by(Video.id.desc()).all()


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    return video
