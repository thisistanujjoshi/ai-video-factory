import asyncio
from dataclasses import dataclass
from pathlib import Path

# No libx264 in this ffmpeg build (patent-restricted distro packaging) --
# libopenh264 is the software H.264 encoder that's actually available.
# Swap here if deploying somewhere with libx264.
VIDEO_CODEC = "libopenh264"
AUDIO_CODEC = "aac"


class RenderError(Exception):
    pass


@dataclass
class SceneRenderInput:
    visual_path: Path
    audio_path: Path
    duration_seconds: float
    # False (default): visual_path is a still image, looped for the scene's
    # duration (ImageProvider). True: visual_path is an already-encoded
    # video clip (VideoProvider) -- its own video stream is used directly,
    # muted, with audio_path's voiceover as the audio track instead.
    visual_is_video: bool = False


async def _run_ffmpeg(args: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RenderError(stderr.decode())


async def render_video(
    work_dir: Path,
    scenes: list[SceneRenderInput],
    captions_srt_path: Path | None,
    output_path: Path,
    resolution: str = "1080x1920",
) -> None:
    """Scene visuals (still images or generated video clips) + per-scene
    voiceover -> per-scene clips -> concat -> caption burn-in -> final MP4.
    Pure ffmpeg orchestration, no LLM calls."""
    width, height = resolution.split("x")

    clip_paths = []
    for index, scene in enumerate(scenes, start=1):
        clip_path = work_dir / f"scene_{index}.mp4"
        input_args = (
            ["-i", str(scene.visual_path)]
            if scene.visual_is_video
            else ["-loop", "1", "-i", str(scene.visual_path)]
        )
        await _run_ffmpeg(
            [
                *input_args,
                "-i",
                str(scene.audio_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-t",
                str(scene.duration_seconds),
                "-vf",
                f"scale={width}:{height},format=yuv420p",
                "-c:v",
                VIDEO_CODEC,
                "-c:a",
                AUDIO_CODEC,
                "-shortest",
                str(clip_path),
            ]
        )
        clip_paths.append(clip_path)

    concat_list = work_dir / "concat.txt"
    concat_list.write_text("".join(f"file '{p}'\n" for p in clip_paths))
    concatenated_path = work_dir / "concatenated.mp4"
    await _run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(concatenated_path)]
    )

    if captions_srt_path is None:
        concatenated_path.replace(output_path)
        return

    await _run_ffmpeg(
        [
            "-i",
            str(concatenated_path),
            "-vf",
            f"subtitles={captions_srt_path}",
            "-c:v",
            VIDEO_CODEC,
            "-c:a",
            "copy",
            str(output_path),
        ]
    )
