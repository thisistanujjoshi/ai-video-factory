import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.video.captions import build_srt
from app.video.renderer import SceneRenderInput, render_video

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _lavfi_png(path: Path, color: str, width: int = 160, height: int = 284) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={width}x{height}:d=1",
            "-frames:v",
            "1",
            str(path),
        ],
        check=True,
    )


def _lavfi_wav(path: Path, duration: float) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            str(duration),
            str(path),
        ],
        check=True,
    )


def _ffprobe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_render_video_produces_a_real_mp4():
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        scenes = []
        for i, (color, duration) in enumerate([("red", 1.0), ("blue", 1.0)], start=1):
            image_path = work_dir / f"in_{i}.png"
            audio_path = work_dir / f"in_{i}.wav"
            _lavfi_png(image_path, color)
            _lavfi_wav(audio_path, duration)
            scenes.append(SceneRenderInput(image_path, audio_path, duration))

        class _S:
            def __init__(self, duration, caption):
                self.duration_seconds = duration
                self.caption = caption

        srt_path = work_dir / "captions.srt"
        srt_path.write_text(build_srt([_S(1.0, "one"), _S(1.0, "two")]))

        output_path = work_dir / "final.mp4"

        import asyncio

        asyncio.run(render_video(work_dir, scenes, srt_path, output_path, resolution="160x284"))

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        probe = _ffprobe(output_path)
        codec_types = {s["codec_type"] for s in probe["streams"]}
        assert codec_types == {"video", "audio"}
        assert 1.8 <= float(probe["format"]["duration"]) <= 2.2
