from string import Template

from sqlalchemy.orm import Session

from app.agents.base import PROMPTS_DIR, generate_structured
from app.models import ContentProfile
from app.providers.llm import LLMProvider
from app.schemas.strategy import GeneratedStrategy

PROMPT_VERSION = "v1"
_TEMPLATE = Template((PROMPTS_DIR / "strategy" / f"{PROMPT_VERSION}.txt").read_text())


class StrategyAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate(
        self, db: Session, profile: ContentProfile, patterns: dict
    ) -> GeneratedStrategy:
        prompt = _TEMPLATE.substitute(
            profile_name=profile.name,
            niche_primary=profile.niche.get("primary", ""),
            hook_types=", ".join(profile.strategy.get("hook_types", [])),
            sample_size=patterns["sample_size"],
            by_emotion=patterns["by_target_emotion"],
            by_duration=patterns["by_duration_bucket"],
            by_platform=patterns["by_platform"],
            top_titles=", ".join(patterns["top_performing_titles"]) or "none yet",
        )

        return await generate_structured(
            db,
            self.llm,
            prompt,
            GeneratedStrategy,
            agent="strategy_agent",
            prompt_version=PROMPT_VERSION,
            input_payload={"content_profile_id": profile.id, "patterns": patterns},
            mode="strategy",
            count=1,
        )
