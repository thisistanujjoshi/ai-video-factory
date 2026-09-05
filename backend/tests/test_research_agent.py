from app.agents.research import ResearchAgent
from app.models import ContentProfile
from app.providers.llm import MockLLMProvider


def _profile(db_session) -> ContentProfile:
    profile = ContentProfile(
        name="Research Test",
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


async def test_generate_persists_research_items(db_session):
    profile = _profile(db_session)
    agent = ResearchAgent(MockLLMProvider())

    items = await agent.generate(db_session, profile, count=3)

    assert len(items) == 3
    for item in items:
        assert item.id is not None
        assert item.content_profile_id == profile.id
        assert 0 <= item.trend_score <= 100
        assert 0 <= item.novelty_score <= 100


async def test_generate_scopes_to_the_given_profile(db_session):
    profile_a = _profile(db_session)
    profile_b = ContentProfile(
        name="Research Test B",
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

    agent = ResearchAgent(MockLLMProvider())
    await agent.generate(db_session, profile_a, count=2)
    items_b = await agent.generate(db_session, profile_b, count=1)

    assert len(items_b) == 1
    assert items_b[0].content_profile_id == profile_b.id
