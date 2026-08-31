from string import Template

from sqlalchemy.orm import Session

from app.agents.base import PROMPTS_DIR, generate_structured
from app.models import ContentProfile, Script, Video
from app.providers.llm import LLMProvider
from app.schemas.qa import QAResult

PROMPT_VERSION = "v1"
_TEMPLATE = Template((PROMPTS_DIR / "qa" / f"{PROMPT_VERSION}.txt").read_text())


class QAAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def review(
        self, db: Session, video: Video, script: Script, profile: ContentProfile
    ) -> QAResult:
        captions_preview = " | ".join(scene.caption for scene in video.scenes)
        prompt = _TEMPLATE.substitute(
            profile_name=profile.name,
            tone=profile.style.get("tone", ""),
            pacing=profile.style.get("pacing", ""),
            title=script.title,
            hook=script.hook,
            narration=script.narration,
            cta=script.cta,
            scene_count=len(video.scenes),
            captions_preview=captions_preview,
        )

        return await generate_structured(
            db,
            self.llm,
            prompt,
            QAResult,
            agent="qa_agent",
            prompt_version=PROMPT_VERSION,
            input_payload={"video_id": video.id},
            mode="qa",
            count=1,
        )
