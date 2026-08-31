from sqlalchemy.orm import Session

from app.agents.scripts import ScriptAgent
from app.agents.storyboard import StoryboardAgent
from app.models import ContentProfile, Idea, Video, VideoState, transition
from app.providers.llm import get_llm_provider


async def generate_video_from_idea(db: Session, idea: Idea, profile: ContentProfile) -> Video:
    """Idea -> script -> storyboard, synchronously (same tradeoff noted
    throughout: no Celery job yet, mock LLM is instant). Shared by the
    POST /videos/generate endpoint and the Phase 9 autonomous cycle, so
    the pipeline logic lives in exactly one place."""
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
