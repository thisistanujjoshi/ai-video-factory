from string import Template

from sqlalchemy.orm import Session

from app.agents.base import PROMPTS_DIR, generate_structured
from app.models import ContentProfile, Scene, Script, Video
from app.providers.llm import LLMProvider
from app.schemas.storyboard import GeneratedStoryboard

PROMPT_VERSION = "v1"
_TEMPLATE = Template((PROMPTS_DIR / "storyboard" / f"{PROMPT_VERSION}.txt").read_text())


class StoryboardAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate(
        self, db: Session, script: Script, profile: ContentProfile, video: Video
    ) -> list[Scene]:
        beat_count = len(script.scenes) or 1
        prompt = _TEMPLATE.substitute(
            aspect_ratio=profile.video.get("aspect_ratio", "9:16"),
            visual_style=profile.style.get("visual_style", ""),
            script_title=script.title,
            narration=script.narration,
            scene_beats="; ".join(beat["narration"] for beat in script.scenes),
        )

        result = await generate_structured(
            db,
            self.llm,
            prompt,
            GeneratedStoryboard,
            agent="storyboard_agent",
            prompt_version=PROMPT_VERSION,
            input_payload={"script_id": script.id},
            mode="storyboard",
            count=beat_count,
        )

        scenes = []
        for generated in result.scenes:
            scene = Scene(
                video_id=video.id,
                scene_number=generated.scene_number,
                duration_seconds=generated.duration_seconds,
                narration=generated.narration,
                visual_prompt=generated.visual_prompt,
                camera_motion=generated.camera_motion,
                caption=generated.caption,
                transition=generated.transition,
                sound_effect=generated.sound_effect,
            )
            db.add(scene)
            scenes.append(scene)
        db.flush()
        return scenes
