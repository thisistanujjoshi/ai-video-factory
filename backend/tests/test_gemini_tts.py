import io
import os
import wave

import pytest

from app.providers.tts import GeminiTTSProvider

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set -- live Gemini test skipped",
)


async def test_gemini_tts_produces_real_narrated_audio():
    """Live call against the real Gemini TTS API. Requires GEMINI_API_KEY
    in the environment (never in a committed file) -- skipped otherwise.
    See app/providers/tts.py for the verified model/format notes."""
    provider = GeminiTTSProvider(os.environ["GEMINI_API_KEY"])
    wav_bytes = await provider.generate_voiceover("No body was ever found.", duration_seconds=3.0)

    with wave.open(io.BytesIO(wav_bytes)) as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() > 0
        duration = wav_file.getnframes() / wav_file.getframerate()
        assert duration > 0.5  # real speech, not an empty clip
