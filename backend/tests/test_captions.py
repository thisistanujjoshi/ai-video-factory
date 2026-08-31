from dataclasses import dataclass

from app.video.captions import build_srt


@dataclass
class _FakeScene:
    duration_seconds: float
    caption: str


def test_build_srt_lays_out_cues_cumulatively():
    scenes = [_FakeScene(3.0, "First"), _FakeScene(2.5, "Second")]
    srt = build_srt(scenes)
    assert "1\n00:00:00,000 --> 00:00:03,000\nFirst\n" in srt
    assert "2\n00:00:03,000 --> 00:00:05,500\nSecond\n" in srt
