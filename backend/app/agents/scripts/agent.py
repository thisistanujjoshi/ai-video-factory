from string import Template

from sqlalchemy.orm import Session

from app.agents.base import PROMPTS_DIR, generate_structured
from app.models import ContentProfile, Idea, Script
from app.providers.llm import LLMProvider
from app.schemas.script import GeneratedScript

PROMPT_VERSION = "v1"
_TEMPLATE = Template((PROMPTS_DIR / "scripts" / f"{PROMPT_VERSION}.txt").read_text())

# HOOK, SETUP, CURIOSITY, ESCALATION, REVEAL, PAYOFF, CTA -- section 14.
_STRUCTURE_BEATS = 7


class ScriptAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate(self, db: Session, idea: Idea, profile: ContentProfile) -> Script:
        prompt = _TEMPLATE.substitute(
            profile_name=profile.name,
            tone=profile.style.get("tone", ""),
            pacing=profile.style.get("pacing", ""),
            narration_style=profile.style.get("narration", ""),
            idea_title=idea.title,
            idea_premise=idea.premise,
            idea_hook=idea.hook,
            min_duration=profile.video.get("min_duration_seconds", 45),
            max_duration=profile.video.get("max_duration_seconds", 75),
        )

        result = await generate_structured(
            db,
            self.llm,
            prompt,
            GeneratedScript,
            agent="script_agent",
            prompt_version=PROMPT_VERSION,
            input_payload={"idea_id": idea.id},
            mode="script",
            count=_STRUCTURE_BEATS,
        )

        script = Script(
            idea_id=idea.id,
            title=result.title,
            hook=result.hook,
            narration=result.narration,
            estimated_duration_seconds=result.estimated_duration_seconds,
            cta=result.cta,
            engagement_question=result.engagement_question,
            scenes=[scene.model_dump() for scene in result.scenes],
        )
        db.add(script)
        db.flush()
        return script
