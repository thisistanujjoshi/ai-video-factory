import json
from abc import ABC, abstractmethod
from typing import Any

from app.config import get_settings


class LLMProvider(ABC):
    """Every AI text-generation call goes through this. No call site talks to
    a specific vendor SDK directly — see Rule 3 in the project spec."""

    model_name: str = "unknown"

    @abstractmethod
    async def generate(self, prompt: str, *, temperature: float = 0.7, **kwargs: Any) -> str:
        """Return raw text output (JSON when the caller needs structured data)."""


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


_MOCK_GENERATORS = {"ideas": _mock_ideas, "script": _mock_script, "storyboard": _mock_storyboard}


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
        mode: str = "text",
        count: int = 1,
        **kwargs: Any,
    ) -> str:
        generator = _MOCK_GENERATORS.get(mode)
        if generator is None:
            return json.dumps({"text": "mock response"})
        return json.dumps(generator(count))


def get_llm_provider() -> LLMProvider:
    provider = get_settings().llm_provider or "mock"
    if provider == "mock":
        return MockLLMProvider()
    raise ValueError(
        f"LLM provider {provider!r} is not implemented yet (real providers land in Phase 5)"
    )
