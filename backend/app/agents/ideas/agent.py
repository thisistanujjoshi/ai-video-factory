from string import Template

from sqlalchemy.orm import Session

from app.agents.base import PROMPTS_DIR, generate_structured
from app.models import ContentProfile, ContentStrategy, Idea, ResearchItem
from app.providers.embedding import EmbeddingProvider, get_embedding_provider
from app.providers.llm import LLMProvider
from app.schemas.idea import GeneratedIdea, GeneratedIdeaList
from app.services.content_memory import is_similar_to_any
from app.services.idea_scoring import score_idea

PROMPT_VERSION = "v2"
_TEMPLATE = Template((PROMPTS_DIR / "ideas" / f"{PROMPT_VERSION}.txt").read_text())


def _dedupe(ideas: list[GeneratedIdea]) -> list[GeneratedIdea]:
    # ponytail: exact-normalized-title dedup catches the LLM literally
    # repeating itself in one batch; embedding similarity (below, applied
    # against DB history) catches near-duplicates across separate calls.
    seen: set[str] = set()
    deduped = []
    for idea in ideas:
        key = idea.title.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(idea)
    return deduped


def _strategy_guidance(strategy: ContentStrategy | None) -> str:
    if strategy is None:
        return "No prior strategy yet -- no performance history to learn from."
    return (
        "Based on performance history, lean into these topics: "
        f"{', '.join(strategy.best_topics) or 'none identified yet'}. "
        f"Best-performing hook types: {', '.join(strategy.best_hook_types) or 'none identified yet'}. "
        f"Target duration: {strategy.recommended_duration.get('min_seconds')}-"
        f"{strategy.recommended_duration.get('max_seconds')}s, "
        f"{strategy.recommended_pacing} pacing. "
        f"Avoid: {', '.join(strategy.avoid_patterns) or 'nothing specific yet'}."
    )


class IdeaAgent:
    def __init__(self, llm: LLMProvider, embedding_provider: EmbeddingProvider | None = None):
        self.llm = llm
        self.embedding_provider = embedding_provider or get_embedding_provider()

    async def generate(
        self,
        db: Session,
        profile: ContentProfile,
        research: ResearchItem | None = None,
        count: int = 20,
        strategy: ContentStrategy | None = None,
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
            strategy_guidance=_strategy_guidance(strategy),
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

        existing_embeddings: list[list[float]] = [
            row.embedding
            for row in db.query(Idea)
            .filter_by(content_profile_id=profile.id)
            .filter(Idea.embedding.isnot(None))
            if row.embedding is not None
        ]

        ideas = []
        for candidate in _dedupe(result.ideas):
            embedding = await self.embedding_provider.embed(
                f"{candidate.title} {candidate.premise}"
            )
            if is_similar_to_any(embedding, existing_embeddings):
                continue  # too similar to existing content (spec section 37) -- skip, don't persist

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
                embedding=embedding,
            )
            db.add(idea)
            ideas.append(idea)
            existing_embeddings.append(embedding)
        db.flush()
        return ideas
