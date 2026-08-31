import json

from pydantic import BaseModel

from app.agents.base import GenerationFailedError, generate_structured
from app.providers.llm import LLMProvider


class _Thing(BaseModel):
    name: str


class _RecordingProvider(LLMProvider):
    model_name = "fake-model"

    def __init__(self, responses: list[str]):
        self._responses = responses
        self.calls: list[dict] = []

    async def generate(self, prompt, *, temperature=0.7, response_schema=None, **kwargs):
        self.calls.append({"prompt": prompt, "response_schema": response_schema, **kwargs})
        return self._responses[len(self.calls) - 1]


async def test_generate_structured_passes_response_schema_to_provider(db_session):
    provider = _RecordingProvider([json.dumps({"name": "ok"})])
    result = await generate_structured(
        db_session, provider, "prompt", _Thing, agent="test", prompt_version="v1", input_payload={}
    )
    assert result.name == "ok"
    assert provider.calls[0]["response_schema"] == _Thing.model_json_schema()


async def test_generate_structured_retries_once_then_logs_failure(db_session):
    provider = _RecordingProvider(["not json", "still not json"])
    try:
        await generate_structured(
            db_session,
            provider,
            "prompt",
            _Thing,
            agent="test",
            prompt_version="v1",
            input_payload={},
        )
        raise AssertionError("expected GenerationFailedError")
    except GenerationFailedError:
        pass
    assert len(provider.calls) == 2  # initial attempt + 1 retry
