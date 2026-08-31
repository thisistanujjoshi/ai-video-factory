import json

from app.agents.ideas import IdeaAgent
from app.models import ContentProfile, ContentStrategy
from app.providers.llm import LLMProvider


class _RecordingLLM(LLMProvider):
    model_name = "recording"

    def __init__(self, canned: dict):
        self.canned = canned
        self.prompts: list[str] = []

    async def generate(self, prompt, *, temperature=0.7, response_schema=None, **kwargs):
        self.prompts.append(prompt)
        return json.dumps(self.canned)


def _profile(db_session) -> ContentProfile:
    profile = ContentProfile(
        name="Strategy Wiring Test",
        niche={"primary": "mystery", "secondary": []},
        audience={"min_age": 18, "max_age": 35, "language": "English"},
        video={
            "type": "short",
            "min_duration_seconds": 30,
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
        strategy={"hook_types": ["curiosity"]},
        publishing={"youtube": True},
        schedule={"videos_per_day": 1},
    )
    db_session.add(profile)
    db_session.flush()
    return profile


async def test_idea_generation_prompt_includes_strategy_guidance(db_session):
    """The acceptance criterion for Phase 8 -- proven directly: a
    ContentStrategy derived from history changes what the IdeaAgent's
    prompt actually asks for next time, not just that a strategy object
    exists somewhere unused."""
    profile = _profile(db_session)
    strategy = ContentStrategy(
        content_profile_id=profile.id,
        best_topics=["haunted lighthouses"],
        best_hook_types=["shocking_fact"],
        recommended_duration={"min_seconds": 50, "max_seconds": 65},
        recommended_pacing="very fast",
        recommended_posting_windows=["weekday evenings"],
        avoid_patterns=["overused 'you won't believe' phrasing"],
        rationale="test",
        sample_size=5,
        patterns={},
    )
    db_session.add(strategy)
    db_session.flush()

    llm = _RecordingLLM({"ideas": []})
    await IdeaAgent(llm).generate(db_session, profile, count=3, strategy=strategy)

    assert len(llm.prompts) == 1
    prompt = llm.prompts[0]
    assert "haunted lighthouses" in prompt
    assert "shocking_fact" in prompt
    assert "overused 'you won't believe' phrasing" in prompt


async def test_idea_generation_without_strategy_says_no_history(db_session):
    profile = _profile(db_session)
    llm = _RecordingLLM({"ideas": []})

    await IdeaAgent(llm).generate(db_session, profile, count=3, strategy=None)

    assert "No prior strategy yet" in llm.prompts[0]
