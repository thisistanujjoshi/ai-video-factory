import os

import pytest

from app.providers.llm import GeminiLLMProvider
from app.schemas.idea import GeneratedIdeaList

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set -- live Gemini test skipped",
)


async def test_gemini_generates_valid_structured_ideas():
    """Live call against the real Gemini API. Requires GEMINI_API_KEY in the
    environment (never in a committed file) -- skipped otherwise, including
    in CI. See app/providers/llm.py for the verified model/latency notes."""
    provider = GeminiLLMProvider(os.environ["GEMINI_API_KEY"])
    raw = await provider.generate(
        "Generate 2 short-form mystery video ideas with plausible scores.",
        response_schema=GeneratedIdeaList.model_json_schema(),
    )
    parsed = GeneratedIdeaList.model_validate_json(raw)
    assert len(parsed.ideas) >= 1
