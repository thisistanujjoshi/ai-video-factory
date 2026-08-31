import os

import pytest

from app.agents.ideas import IdeaAgent
from app.agents.qa import QAAgent
from app.agents.scripts import ScriptAgent
from app.agents.storyboard import StoryboardAgent
from app.models import ContentProfile, Video, VideoState
from app.providers.llm import GeminiLLMProvider

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set -- live Gemini test skipped",
)


async def test_real_gemini_drives_the_idea_to_qa_pipeline(db_session):
    """Same idea->script->storyboard->QA pipeline as test_pipeline_e2e.py,
    but with a real GeminiLLMProvider instead of the mock -- proves the
    prompts/schemas actually work against the real API, not just canned
    mock JSON. Live call, requires GEMINI_API_KEY; skipped otherwise."""
    llm = GeminiLLMProvider(os.environ["GEMINI_API_KEY"])

    profile = ContentProfile(
        name="Gemini E2E Test Profile",
        niche={"primary": "mystery", "secondary": ["unexplained"]},
        audience={"min_age": 18, "max_age": 35, "language": "English"},
        video={
            "type": "short",
            "min_duration_seconds": 20,
            "max_duration_seconds": 90,
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
        },
        style={
            "tone": "mysterious",
            "pacing": "fast",
            "narration": "dramatic",
            "visual_style": "cinematic",
        },
        strategy={"hook_types": ["curiosity", "question"]},
        publishing={"youtube": True, "instagram": True, "tiktok": True},
        schedule={"videos_per_day": 1},
    )
    db_session.add(profile)
    db_session.flush()

    ideas = await IdeaAgent(llm).generate(db_session, profile, count=3)
    assert len(ideas) >= 1
    best_idea = max(ideas, key=lambda i: i.overall_score)

    script = await ScriptAgent(llm).generate(db_session, best_idea, profile)
    assert script.narration
    assert len(script.scenes) > 0

    video = Video(content_profile_id=profile.id, idea_id=best_idea.id, state=VideoState.DRAFT)
    db_session.add(video)
    db_session.flush()

    scenes = await StoryboardAgent(llm).generate(db_session, script, profile, video)
    assert len(scenes) > 0
    for scene in scenes:
        assert scene.visual_prompt
        assert scene.duration_seconds > 0

    qa_result = await QAAgent(llm).review(db_session, video, script, profile)
    assert 0 <= qa_result.score <= 100
