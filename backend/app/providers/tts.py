import asyncio
import io
import wave
from abc import ABC, abstractmethod

from app.config import get_settings


class TTSProvider(ABC):
    @abstractmethod
    async def generate_voiceover(
        self, text: str, *, duration_seconds: float, voice: str = "default"
    ) -> bytes:
        """Return raw WAV bytes narrating `text`. `duration_seconds` is a
        target/hint (the mock hits it exactly since it's silence; real
        speech naturally runs long or short depending on the text) -- a
        caller that needs the real length should measure the returned
        WAV, not assume it matches what was asked for."""


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


def _pcm_to_wav(pcm: bytes, *, sample_rate: int, sample_width: int = 2, channels: int = 1) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return buffer.getvalue()


def _parse_pcm_mime_type(mime_type: str) -> int:
    """Gemini returns e.g. 'audio/L16;codec=pcm;rate=24000' -- pull the
    sample rate out; default to 24000 (its current default) if the format
    ever changes shape and the rate isn't there."""
    for part in mime_type.split(";"):
        if part.strip().startswith("rate="):
            return int(part.strip().removeprefix("rate="))
    return 24000


class GeminiTTSError(RuntimeError):
    pass


class GeminiTTSProvider(TTSProvider):
    """Google Gemini's text-to-speech models via `google-genai`.

    IMPLEMENTED — LIVE TESTED 2026-08-31 against `gemini-2.5-flash-preview-tts`:
    real narrated speech, ~3s response time, returns raw 16-bit mono PCM
    (`audio/L16;codec=pcm;rate=24000`), wrapped into a proper WAV container
    here since that's what the rest of the pipeline expects.
    """

    model_name = "gemini-2.5-flash-preview-tts"
    default_voice = "Kore"

    def __init__(self, api_key: str, model: str | None = None):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        if model:
            self.model_name = model

    async def generate_voiceover(
        self, text: str, *, duration_seconds: float, voice: str = "default"
    ) -> bytes:
        from google.genai import types

        voice_name = self.default_voice if voice == "default" else voice
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )
        response = await self._client.aio.models.generate_content(
            model=self.model_name, contents=text, config=config
        )
        candidates = response.candidates or []
        parts = candidates[0].content.parts if candidates and candidates[0].content else None
        inline_data = parts[0].inline_data if parts else None
        if inline_data is None or inline_data.data is None:
            # A quota/rate-limit hit here doesn't always surface as an
            # exception (unlike a plain 429, which does raise) -- seen in
            # practice as a silently empty response instead. finish_reason
            # and prompt_feedback are the two fields worth checking first.
            finish_reason = candidates[0].finish_reason if candidates else None
            raise GeminiTTSError(
                f"Gemini returned no audio for this narration (finish_reason={finish_reason}, "
                f"prompt_feedback={response.prompt_feedback}) -- often a quota/rate limit "
                "(free tier: 10 requests/day for this model) rather than a real content issue"
            )

        sample_rate = _parse_pcm_mime_type(inline_data.mime_type or "")
        return _pcm_to_wav(inline_data.data, sample_rate=sample_rate)


def get_tts_provider() -> TTSProvider:
    settings = get_settings()
    provider = settings.tts_provider or "mock"
    if provider == "mock":
        return MockTTSProvider()
    if provider == "gemini":
        if not settings.tts_api_key:
            raise ValueError("TTS_API_KEY is required when TTS_PROVIDER=gemini")
        return GeminiTTSProvider(settings.tts_api_key)
    raise ValueError(f"TTS provider {provider!r} is not implemented (mock, gemini are available)")
