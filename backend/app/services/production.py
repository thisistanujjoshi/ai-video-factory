import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Asset, AudioAsset, ContentProfile, Video, VideoState, transition
from app.providers.image import get_image_provider
from app.providers.tts import get_tts_provider
from app.storage import get_storage_provider
from app.video.captions import build_srt
from app.video.renderer import SceneRenderInput, render_video

# ponytail: this is a plain service, not an "agent" -- it calls no LLM.
# Asset/voiceover generation and rendering are traditional-code concerns
# per Rule 4 (deterministic, provider- and ffmpeg-driven), so it doesn't
# belong in app/agents alongside the LLM-calling idea/script/storyboard
# agents even though the spec's directory sketch put "production" there.


async def produce_video(db: Session, video: Video, profile: ContentProfile) -> None:
    """Storyboard -> real MP4: per-scene image + voiceover, ffmpeg render,
    caption burn-in. Raises on failure after marking the video FAILED."""
    storage = get_storage_provider()
    image_provider = get_image_provider()
    tts_provider = get_tts_provider()
    resolution = profile.video.get("resolution", "1080x1920")
    width, height = (int(part) for part in resolution.split("x"))

    try:
        transition(video, VideoState.ASSETS_GENERATING)

        with tempfile.TemporaryDirectory(prefix=f"video_{video.id}_") as tmp:
            work_dir = Path(tmp)
            render_inputs = []

            for scene in video.scenes:
                image_bytes = await image_provider.generate_image(
                    scene.visual_prompt, width=width, height=height
                )
                image_path = await storage.upload(
                    f"videos/{video.id}/scenes/{scene.scene_number}/image.png", image_bytes
                )
                db.add(
                    Asset(
                        video_id=video.id,
                        scene_id=scene.id,
                        type="image",
                        provider=type(image_provider).__name__,
                        source="mock",
                        path=image_path,
                    )
                )

                audio_bytes = await tts_provider.generate_voiceover(
                    scene.narration, duration_seconds=scene.duration_seconds
                )
                audio_path = await storage.upload(
                    f"videos/{video.id}/scenes/{scene.scene_number}/voiceover.wav", audio_bytes
                )
                db.add(
                    AudioAsset(
                        video_id=video.id,
                        scene_id=scene.id,
                        kind="voiceover",
                        provider=type(tts_provider).__name__,
                        path=audio_path,
                        duration_seconds=scene.duration_seconds,
                    )
                )

                render_inputs.append(
                    SceneRenderInput(
                        image_path=Path(image_path),
                        audio_path=Path(audio_path),
                        duration_seconds=scene.duration_seconds,
                    )
                )

            transition(video, VideoState.ASSETS_READY)
            transition(video, VideoState.RENDERING)

            srt_path = work_dir / "captions.srt"
            srt_path.write_text(build_srt(video.scenes))

            local_output = work_dir / "final.mp4"
            await render_video(
                work_dir, render_inputs, srt_path, local_output, resolution=resolution
            )

            final_bytes = local_output.read_bytes()
            video.rendered_path = await storage.upload(f"videos/{video.id}/final.mp4", final_bytes)

        transition(video, VideoState.RENDERED)
        db.commit()
    except Exception:
        db.rollback()
        video.state = VideoState.FAILED
        db.commit()
        raise
