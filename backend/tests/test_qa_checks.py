import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.video.qa_checks import run_technical_checks

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@dataclass
class _FakeProfile:
    video: dict


@dataclass
class _FakeScene:
    caption: str


def _make_mp4(path: Path, width: int, height: int, duration: float) -> None:
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
            f"color=c=red:s={width}x{height}:d={duration}",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            str(duration),
            "-vf",
            "format=yuv420p",
            "-c:v",
            "libopenh264",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
    )


def test_technical_checks_pass_for_matching_video():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "good.mp4"
        _make_mp4(path, 320, 568, 5.0)
        profile = _FakeProfile(
            video={
                "resolution": "320x568",
                "aspect_ratio": "9:16",
                "min_duration_seconds": 3,
                "max_duration_seconds": 10,
            }
        )
        result = run_technical_checks(path, profile, [_FakeScene("hi")])
        assert result.passed, result.issues


def test_technical_checks_fail_on_duration_out_of_range():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "short.mp4"
        _make_mp4(path, 320, 568, 2.0)
        profile = _FakeProfile(
            video={
                "resolution": "320x568",
                "aspect_ratio": "9:16",
                "min_duration_seconds": 45,
                "max_duration_seconds": 75,
            }
        )
        result = run_technical_checks(path, profile, [_FakeScene("hi")])
        assert not result.passed
        assert any("duration" in issue for issue in result.issues)


def test_technical_checks_fail_on_missing_file():
    profile = _FakeProfile(video={"resolution": "320x568", "aspect_ratio": "9:16"})
    result = run_technical_checks(Path("/nonexistent/path.mp4"), profile, [])
    assert not result.passed
    assert result.issues
