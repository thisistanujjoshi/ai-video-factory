import shutil
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.providers.video import (
    GeminiVideoError,
    GeminiVideoProvider,
    MockVideoProvider,
    get_video_provider,
)

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _ffprobe_video_stream(path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height",
            "-of",
            "default=noprint_wrappers=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return dict(line.split("=") for line in result.stdout.strip().splitlines())


async def test_mock_video_provider_produces_a_playable_clip(tmp_path):
    provider = MockVideoProvider()
    data = await provider.generate_video_clip(
        "a foggy lighthouse at dusk", duration_seconds=1.5, width=160, height=284
    )
    out = tmp_path / "clip.mp4"
    out.write_bytes(data)

    info = _ffprobe_video_stream(out)
    assert info["codec_name"] == "h264"
    assert info["width"] == "160"
    assert info["height"] == "284"


async def test_mock_video_provider_is_deterministic_per_prompt():
    provider = MockVideoProvider()
    a = await provider.generate_video_clip("prompt A", duration_seconds=1.0, width=160, height=284)
    b = await provider.generate_video_clip("prompt A", duration_seconds=1.0, width=160, height=284)
    c = await provider.generate_video_clip("prompt B", duration_seconds=1.0, width=160, height=284)
    assert a == b
    assert a != c


def test_get_video_provider_defaults_to_none_when_unset(monkeypatch):
    monkeypatch.setenv("VIDEO_PROVIDER", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        assert get_video_provider() is None
    finally:
        get_settings.cache_clear()


def test_get_video_provider_gemini_requires_api_key(monkeypatch):
    monkeypatch.setenv("VIDEO_PROVIDER", "gemini")
    monkeypatch.setenv("VIDEO_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="VIDEO_API_KEY"):
            get_video_provider()
    finally:
        get_settings.cache_clear()


async def test_gemini_video_provider_polls_until_done_then_returns_bytes(monkeypatch):
    """Exercises the operation-polling loop against a faked SDK response
    shape (verified against the real installed SDK's type signatures --
    see GeminiVideoProvider's docstring for what wasn't live-testable)."""
    provider = GeminiVideoProvider(api_key="fake", poll_interval_seconds=0)

    pending_op = SimpleNamespace(done=False, error=None, response=None)
    done_op = SimpleNamespace(
        done=True,
        error=None,
        response=SimpleNamespace(
            generated_videos=[
                SimpleNamespace(
                    video=SimpleNamespace(
                        video_bytes=b"fake-mp4-bytes", uri=None, mime_type="video/mp4"
                    )
                )
            ]
        ),
    )

    provider._client = SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_videos=AsyncMock(return_value=pending_op)),
            operations=SimpleNamespace(get=AsyncMock(return_value=done_op)),
        )
    )

    result = await provider.generate_video_clip("a prompt", duration_seconds=4.0)
    assert result == b"fake-mp4-bytes"


async def test_gemini_video_provider_raises_on_operation_error(monkeypatch):
    provider = GeminiVideoProvider(api_key="fake", poll_interval_seconds=0)
    failed_op = SimpleNamespace(done=True, error="quota exceeded", response=None)
    provider._client = SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_videos=AsyncMock(return_value=failed_op))
        )
    )

    with pytest.raises(GeminiVideoError, match="quota exceeded"):
        await provider.generate_video_clip("a prompt", duration_seconds=4.0)


async def test_gemini_video_provider_times_out_if_never_done(monkeypatch):
    provider = GeminiVideoProvider(api_key="fake", poll_interval_seconds=0, max_wait_seconds=0)
    pending_op = SimpleNamespace(done=False, error=None, response=None)
    provider._client = SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_videos=AsyncMock(return_value=pending_op)),
            operations=SimpleNamespace(get=AsyncMock(return_value=pending_op)),
        )
    )

    with pytest.raises(GeminiVideoError, match="did not finish"):
        await provider.generate_video_clip("a prompt", duration_seconds=4.0)
