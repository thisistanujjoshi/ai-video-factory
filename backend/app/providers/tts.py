import asyncio
from abc import ABC, abstractmethod

from app.config import get_settings


class TTSProvider(ABC):
    @abstractmethod
    async def generate_voiceover(
        self, text: str, *, duration_seconds: float, voice: str = "default"
    ) -> bytes:
        """Return raw WAV bytes for the narration `text`, timed to `duration_seconds`."""


class MockTTSProvider(TTSProvider):
    """Silent audio of the requested duration via ffmpeg's lavfi anullsrc --
    no TTS API key, no new dependency. Real providers (Phase 5) actually
    synthesize `text`."""

    async def generate_voiceover(
        self, text: str, *, duration_seconds: float, voice: str = "default"
    ) -> bytes:
        duration = max(duration_seconds, 0.1)
        proc = await asyncio.create_subprocess_exec(
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
            "-f",
            "wav",
            "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed generating mock voiceover: {stderr.decode()}")
        return stdout


def get_tts_provider() -> TTSProvider:
    provider = get_settings().tts_provider or "mock"
    if provider == "mock":
        return MockTTSProvider()
    raise ValueError(
        f"TTS provider {provider!r} is not implemented yet (real providers land in Phase 5)"
    )
