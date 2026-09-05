from string import Template

from sqlalchemy.orm import Session

from app.agents.base import PROMPTS_DIR, generate_structured
from app.models import ContentProfile, ResearchItem
from app.providers.llm import LLMProvider
from app.schemas.research import GeneratedResearchList

PROMPT_VERSION = "v1"
_TEMPLATE = Template((PROMPTS_DIR / "research" / f"{PROMPT_VERSION}.txt").read_text())


class ResearchAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate(
        self, db: Session, profile: ContentProfile, count: int = 5
    ) -> list[ResearchItem]:
        prompt = _TEMPLATE.substitute(
            profile_name=profile.name,
            niche_primary=profile.niche.get("primary", ""),
            niche_secondary=", ".join(profile.niche.get("secondary", [])),
            audience_min=profile.audience.get("min_age", ""),
            audience_max=profile.audience.get("max_age", ""),
            audience_language=profile.audience.get("language", "English"),
            count=count,
        )

        result = await generate_structured(
            db,
            self.llm,
            prompt,
            GeneratedResearchList,
            agent="research_agent",
            prompt_version=PROMPT_VERSION,
            input_payload={"content_profile_id": profile.id, "count": count},
            mode="research",
            count=count,
        )

        items = [
            ResearchItem(
                content_profile_id=profile.id,
                topic=candidate.topic,
                summary=candidate.summary,
                why_now=candidate.why_now,
                trend_score=candidate.trend_score,
                novelty_score=candidate.novelty_score,
                sources=candidate.sources,
            )
            for candidate in result.items
        ]
        db.add_all(items)
        db.flush()
        return items
