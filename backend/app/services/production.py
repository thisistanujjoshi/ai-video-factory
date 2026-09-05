import io
import tempfile
import wave
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Asset, AudioAsset, ContentProfile, Video, VideoState, transition
from app.providers.image import get_image_provider
from app.providers.tts import get_tts_provider
from app.providers.video import get_video_provider
from app.storage import get_storage_provider
from app.video.captions import build_srt
from app.video.renderer import SceneRenderInput, render_video

# ponytail: this is a plain service, not an "agent" -- it calls no LLM.
# Asset/voiceover generation and rendering are traditional-code concerns
# per Rule 4 (deterministic, provider- and ffmpeg-driven), so it doesn't
# belong in app/agents alongside the LLM-calling idea/script/storyboard
# agents even though the spec's directory sketch put "production" there.


def _wav_duration_seconds(wav_bytes: bytes) -> float:
    """The storyboard's `duration_seconds` is a plan, not a guarantee --
    the mock TTS hits it exactly (it's silence), but real narration runs
    however long the sentence takes to say. Scenes get retimed to the
    actual voiceover length so captions and the render stay in sync with
    what's actually playing, rather than drifting from an LLM's guess."""
    with wave.open(io.BytesIO(wav_bytes)) as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


async def produce_video(db: Session, video: Video, profile: ContentProfile) -> None:
    """Storyboard -> real MP4: per-scene visual (image, or a real video
    clip when VIDEO_PROVIDER is configured -- see app/providers/video.py)
    + voiceover, ffmpeg render, caption burn-in. Raises on failure after
    marking the video FAILED.

    ponytail: a real VideoProvider makes per-scene generation minutes-long
    instead of instant (mock) or seconds (TTS/images) -- this still runs
    synchronously in the request handler like the rest of this pipeline,
    which will likely time out in practice with VIDEO_PROVIDER=gemini.
    Not solved here; see BUILD_STATUS.md.
    """
    storage = get_storage_provider()
    image_provider = get_image_provider()
    tts_provider = get_tts_provider()
    video_provider = get_video_provider()
    resolution = profile.video.get("resolution", "1080x1920")
    width, height = (int(part) for part in resolution.split("x"))

    try:
        transition(video, VideoState.ASSETS_GENERATING)

        with tempfile.TemporaryDirectory(prefix=f"video_{video.id}_") as tmp:
            work_dir = Path(tmp)
            render_inputs = []

            # Visual and voiceover are committed independently (right after
            # each provider call, below) and reused here if already present --
            # so a failure anywhere in this loop (e.g. the TTS call for scene
            # 2) can't undo a visual that already generated successfully
            # (e.g. scene 2's own image, or all of scene 1). Without this, a
            # retry would re-roll every not-yet-committed asset from scratch,
            # and a real (non-deterministic) provider could render a
            # different-looking character than the attempt before it.
            existing_visuals = {a.scene_id: a for a in db.query(Asset).filter_by(video_id=video.id)}
            existing_audio = {
                a.scene_id: a
                for a in db.query(AudioAsset).filter_by(video_id=video.id, kind="voiceover")
            }

            for scene in video.scenes:
                visual_asset = existing_visuals.get(scene.id)
                if visual_asset is not None:
                    visual_path = visual_asset.path
                    visual_is_video = visual_asset.type == "video"
                else:
                    if video_provider is not None:
                        visual_bytes = await video_provider.generate_video_clip(
                            scene.visual_prompt,
                            duration_seconds=scene.duration_seconds,
                            width=width,
                            height=height,
                        )
                        visual_path = await storage.upload(
                            f"videos/{video.id}/scenes/{scene.scene_number}/clip.mp4", visual_bytes
                        )
                        asset_type = "video"
                        asset_provider: object = video_provider
                    else:
                        visual_bytes = await image_provider.generate_image(
                            scene.visual_prompt, width=width, height=height
                        )
                        visual_path = await storage.upload(
                            f"videos/{video.id}/scenes/{scene.scene_number}/image.png", visual_bytes
                        )
                        asset_type = "image"
                        asset_provider = image_provider

                    db.add(
                        Asset(
                            video_id=video.id,
                            scene_id=scene.id,
                            type=asset_type,
                            provider=type(asset_provider).__name__,
                            source=(
                                "mock"
                                if asset_type == "image"
                                else type(asset_provider).__name__.lower()
                            ),
                            path=visual_path,
                        )
                    )
                    db.commit()
                    visual_is_video = video_provider is not None

                audio_asset = existing_audio.get(scene.id)
                if audio_asset is not None:
                    audio_path = audio_asset.path
                    actual_duration = audio_asset.duration_seconds
                else:
                    audio_bytes = await tts_provider.generate_voiceover(
                        scene.narration, duration_seconds=scene.duration_seconds
                    )
                    actual_duration = _wav_duration_seconds(audio_bytes)

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
                            duration_seconds=actual_duration,
                        )
                    )
                    db.commit()

                scene.duration_seconds = actual_duration  # retime to the real voiceover length
                db.commit()

                render_inputs.append(
                    SceneRenderInput(
                        visual_path=Path(visual_path),
                        audio_path=Path(audio_path),
                        duration_seconds=actual_duration,
                        visual_is_video=visual_is_video,
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
