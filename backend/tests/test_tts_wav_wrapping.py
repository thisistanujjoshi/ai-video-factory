import io
import wave

from app.providers.tts import _parse_pcm_mime_type, _pcm_to_wav


def test_parse_pcm_mime_type_extracts_rate():
    assert _parse_pcm_mime_type("audio/L16;codec=pcm;rate=24000") == 24000


def test_parse_pcm_mime_type_defaults_when_rate_missing():
    assert _parse_pcm_mime_type("audio/wav") == 24000


def test_pcm_to_wav_produces_a_valid_readable_wav():
    sample_rate = 24000
    duration_seconds = 0.5
    frame_count = int(sample_rate * duration_seconds)
    pcm = b"\x00\x00" * frame_count  # silence, 16-bit mono

    wav_bytes = _pcm_to_wav(pcm, sample_rate=sample_rate)

    with wave.open(io.BytesIO(wav_bytes)) as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == sample_rate
        assert wav_file.getnframes() == frame_count
