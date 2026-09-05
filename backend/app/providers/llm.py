import json
from abc import ABC, abstractmethod
from typing import Any

from app.config import get_settings


class LLMProvider(ABC):
    """Every AI text-generation call goes through this. No call site talks to
    a specific vendor SDK directly — see Rule 3 in the project spec."""

    model_name: str = "unknown"

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        response_schema: dict | None = None,
        **kwargs: Any,
    ) -> str:
        """Return raw text output. When `response_schema` (a Pydantic
        `.model_json_schema()` dict) is given, a provider that supports
        schema-constrained decoding should use it; one that doesn't can
        ignore it and rely on the prompt alone."""


def _mock_ideas(count: int) -> dict:
    return {
        "ideas": [
            {
                "title": f"Mystery Idea {i + 1}",
                "premise": f"A premise for candidate idea {i + 1}.",
                "hook": f"You won't believe what happened in case {i + 1}...",
                "target_emotion": "curiosity",
                "format": "narrated",
                "estimated_duration": 60,
                "difficulty": "medium",
                "scores": {
                    "curiosity": 70 + (i % 20),
                    "emotion": 60 + (i % 25),
                    "trend": 50 + (i % 30),
                    "novelty": 65 + (i % 20),
                    "shareability": 55 + (i % 25),
                    "production_cost": 60 + (i % 15),
                },
            }
            for i in range(count)
        ]
    }


def _mock_script(count: int) -> dict:
    return {
        "title": "Mock Script Title",
        "hook": "You won't believe what happened next.",
        "narration": " ".join(f"Beat {i + 1} narration." for i in range(count)),
        "estimated_duration_seconds": 60.0,
        "cta": "Follow for more.",
        "engagement_question": "Have you ever experienced this?",
        "scenes": [
            {"scene_number": i + 1, "narration": f"Beat {i + 1} narration."} for i in range(count)
        ],
    }


def _mock_storyboard(count: int) -> dict:
    return {
        "scenes": [
            {
                "scene_number": i + 1,
                "duration_seconds": 6.0,
                "narration": f"Beat {i + 1} narration.",
                "visual_prompt": f"Cinematic shot illustrating beat {i + 1}.",
                "camera_motion": "slow_push",
                "caption": f"Beat {i + 1}",
                "transition": "cut",
                "sound_effect": None,
            }
            for i in range(count)
        ]
    }


def _mock_research(count: int) -> dict:
    return {
        "items": [
            {
                "topic": f"Mock Research Topic {i + 1}",
                "summary": f"Summary of a trending angle {i + 1} in this niche.",
                "why_now": f"Why angle {i + 1} is timely right now.",
                "trend_score": 60 + (i % 30),
                "novelty_score": 55 + (i % 35),
                "sources": [],
            }
            for i in range(count)
        ]
    }


def _mock_qa(count: int) -> dict:
    # ponytail: always approves, deliberately. Mock content is bland but
    # never actually bad, so there's nothing for a content review to catch
    # here -- the technical checks (app/video/qa_checks.py) are what Phase 3
    # tests exercise for automatic rejection. A real LLM (Phase 5) will
    # sometimes disapprove real content; nothing downstream assumes it can't.
    return {
        "approved": True,
        "score": 88,
        "issues": [],
        "recommendations": [],
    }


def _mock_strategy(count: int) -> dict:
    return {
        "best_topics": ["unsolved disappearances", "cold cases"],
        "best_hook_types": ["curiosity", "question"],
        "recommended_duration": {"min_seconds": 45, "max_seconds": 75},
        "recommended_pacing": "fast",
        "recommended_posting_windows": ["evenings", "weekends"],
        "avoid_patterns": ["repeating the same hook phrasing across videos"],
        "rationale": "Mock strategy -- not derived from real performance data.",
    }


_MOCK_GENERATORS = {
    "research": _mock_research,
    "ideas": _mock_ideas,
    "script": _mock_script,
    "storyboard": _mock_storyboard,
    "qa": _mock_qa,
    "strategy": _mock_strategy,
}


class MockLLMProvider(LLMProvider):
    """Deterministic canned output so the pipeline runs with no API key or spend.

    `mode`/`count` are internal to the mock (picks + sizes a canned response);
    a real provider ignores them and relies on the prompt + response schema.
    """

    model_name = "mock-llm"

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        response_schema: dict | None = None,
        mode: str = "text",
        count: int = 1,
        **kwargs: Any,
    ) -> str:
        generator = _MOCK_GENERATORS.get(mode)
        if generator is None:
            return json.dumps({"text": "mock response"})
        return json.dumps(generator(count))


class GeminiLLMProvider(LLMProvider):
    """Google Gemini (via the `google-genai` SDK). Uses `response_json_schema`
    for schema-constrained decoding when the caller supplies one -- Gemini
    supports the Pydantic-shaped subset of JSON Schema directly ($defs/$ref,
    minimum/maximum, etc.), so `response_model.model_json_schema()` is passed
    through unmodified rather than translated into the SDK's own `Schema` type.

    Verified live 2026-08-31 against `gemini-flash-lite-latest`: plain text
    (~29s) and schema-constrained JSON (~1-2s, correctly structured, round
    trips through Pydantic `.model_validate_json()`) both work.
    """

    model_name = "gemini-flash-lite-latest"

    def __init__(self, api_key: str, model: str | None = None):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        if model:
            self.model_name = model

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        response_schema: dict | None = None,
        **kwargs: Any,
    ) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json" if response_schema else None,
            response_json_schema=response_schema,
        )
        response = await self._client.aio.models.generate_content(
            model=self.model_name, contents=prompt, config=config
        )
        return response.text or ""


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider or "mock"
    if provider == "mock":
        return MockLLMProvider()
    if provider == "gemini":
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=gemini")
        return GeminiLLMProvider(settings.llm_api_key)
    raise ValueError(f"LLM provider {provider!r} is not implemented (mock, gemini are available)")
