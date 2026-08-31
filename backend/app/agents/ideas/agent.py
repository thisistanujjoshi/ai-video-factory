from string import Template

from sqlalchemy.orm import Session

from app.agents.base import PROMPTS_DIR, generate_structured
from app.models import ContentProfile, Idea, ResearchItem
from app.providers.llm import LLMProvider
from app.schemas.idea import GeneratedIdea, GeneratedIdeaList
from app.services.idea_scoring import score_idea

PROMPT_VERSION = "v1"
_TEMPLATE = Template((PROMPTS_DIR / "ideas" / f"{PROMPT_VERSION}.txt").read_text())


def _dedupe(ideas: list[GeneratedIdea]) -> list[GeneratedIdea]:
    # ponytail: exact-normalized-title dedup, not semantic similarity.
    # Embedding-based dedup across the whole content history is section 37
    # (Content Memory) -- separate feature, not needed to satisfy Phase 1.
    seen: set[str] = set()
    deduped = []
    for idea in ideas:
        key = idea.title.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(idea)
    return deduped


class IdeaAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate(
        self,
        db: Session,
        profile: ContentProfile,
        research: ResearchItem | None = None,
        count: int = 20,
    ) -> list[Idea]:
        prompt = _TEMPLATE.substitute(
            profile_name=profile.name,
            niche_primary=profile.niche.get("primary", ""),
            niche_secondary=", ".join(profile.niche.get("secondary", [])),
            audience_min=profile.audience.get("min_age", ""),
            audience_max=profile.audience.get("max_age", ""),
            audience_language=profile.audience.get("language", "English"),
            tone=profile.style.get("tone", ""),
            pacing=profile.style.get("pacing", ""),
            hook_types=", ".join(profile.strategy.get("hook_types", [])),
            research_context=(
                f"Research angle: {research.summary}" if research else "No prior research supplied."
            ),
            count=count,
        )

        result = await generate_structured(
            db,
            self.llm,
            prompt,
            GeneratedIdeaList,
            agent="idea_agent",
            prompt_version=PROMPT_VERSION,
            input_payload={"content_profile_id": profile.id, "count": count},
            mode="ideas",
            count=count,
        )

        ideas = []
        for candidate in _dedupe(result.ideas):
            scores = candidate.scores.model_dump()
            idea = Idea(
                content_profile_id=profile.id,
                research_item_id=research.id if research else None,
                title=candidate.title,
                premise=candidate.premise,
                hook=candidate.hook,
                target_emotion=candidate.target_emotion,
                format=candidate.format,
                estimated_duration=candidate.estimated_duration,
                difficulty=candidate.difficulty,
                scores=scores,
                overall_score=score_idea(scores),
            )
            db.add(idea)
            ideas.append(idea)
        db.flush()
        return ideas
