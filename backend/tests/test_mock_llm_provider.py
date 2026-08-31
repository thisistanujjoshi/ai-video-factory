import pytest

from app.providers.llm import MockLLMProvider
from app.schemas.idea import GeneratedIdeaList
from app.schemas.script import GeneratedScript
from app.schemas.storyboard import GeneratedStoryboard


@pytest.mark.parametrize(
    ("mode", "count", "response_model"),
    [
        ("ideas", 20, GeneratedIdeaList),
        ("script", 7, GeneratedScript),
        ("storyboard", 5, GeneratedStoryboard),
    ],
)
async def test_mock_provider_output_matches_schema(mode, count, response_model):
    raw = await MockLLMProvider().generate("irrelevant prompt", mode=mode, count=count)
    parsed = response_model.model_validate_json(raw)
    items = parsed.ideas if mode == "ideas" else parsed.scenes
    assert len(items) == count
