import json

from app.agents.ideas import IdeaAgent
from app.models import ContentProfile
from app.providers.llm import LLMProvider

_IDEA = {
    "title": "The Vanishing Hiker of Blackwood Trail",
    "premise": "A hiker disappeared without a trace in 1987.",
    "hook": "No body was ever found.",
    "target_emotion": "fear",
    "format": "narrated",
    "estimated_duration": 60,
    "difficulty": "medium",
    "scores": {
        "curiosity": 80,
        "emotion": 80,
        "trend": 60,
        "novelty": 70,
        "shareability": 75,
        "production_cost": 60,
    },
}

_NEAR_DUPLICATE = {
    **_IDEA,
    "premise": "A hiker vanished without a trace back in 1987.",  # same story, reworded
}

_DIFFERENT = {
    "title": "The Shipwreck Off Sicily",
    "premise": "Divers found a Roman shipwreck with lost treasure off the coast of Sicily.",
    "hook": "It sat undiscovered for two thousand years.",
    "target_emotion": "curiosity",
    "format": "narrated",
    "estimated_duration": 55,
    "difficulty": "medium",
    "scores": {
        "curiosity": 85,
        "emotion": 60,
        "trend": 50,
        "novelty": 90,
        "shareability": 80,
        "production_cost": 65,
    },
}


class _ScriptedLLM(LLMProvider):
    model_name = "scripted"

    def __init__(self, batches: list[list[dict]]):
        self._batches = iter(batches)

    async def generate(self, prompt, *, temperature=0.7, response_schema=None, **kwargs):
        return json.dumps({"ideas": next(self._batches)})


def _profile(db_session) -> ContentProfile:
    profile = ContentProfile(
        name="Dedup Test",
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


async def test_near_duplicate_idea_across_calls_is_rejected(db_session):
    profile = _profile(db_session)
    llm = _ScriptedLLM([[_IDEA], [_NEAR_DUPLICATE, _DIFFERENT]])
    agent = IdeaAgent(llm)

    first_batch = await agent.generate(db_session, profile, count=1)
    assert len(first_batch) == 1

    second_batch = await agent.generate(db_session, profile, count=2)

    titles = {idea.title for idea in second_batch}
    assert (
        "The Vanishing Hiker of Blackwood Trail" not in titles
    )  # rejected as too similar to first_batch
    assert "The Shipwreck Off Sicily" in titles  # genuinely different, kept


async def test_second_profile_is_not_affected_by_first_profiles_history(db_session):
    """Similarity search is scoped per content_profile_id -- a different
    channel isn't blocked from covering the same real-world story."""
    profile_a = _profile(db_session)
    profile_b = ContentProfile(
        name="Dedup Test B",
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
    db_session.add(profile_b)
    db_session.flush()

    await IdeaAgent(_ScriptedLLM([[_IDEA]])).generate(db_session, profile_a, count=1)
    second = await IdeaAgent(_ScriptedLLM([[_NEAR_DUPLICATE]])).generate(
        db_session, profile_b, count=1
    )

    assert len(second) == 1
