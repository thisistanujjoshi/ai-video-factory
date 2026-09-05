import shutil

import pytest

from app.models import Video, VideoState, transition
from app.providers.image import MockImageProvider
from app.providers.tts import MockTTSProvider
from app.services.production import produce_video

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


class _CountingImageProvider(MockImageProvider):
    def __init__(self):
        self.calls: list[str] = []

    async def generate_image(self, prompt, *, width=1080, height=1920):
        self.calls.append(prompt)
        return await super().generate_image(prompt, width=width, height=height)


class _FlakyTTSProvider(MockTTSProvider):
    """Fails the first time it's asked to narrate `fail_on_narration`, then
    succeeds on every later call -- simulates a transient error partway
    through a multi-scene video."""

    def __init__(self, fail_on_narration: str):
        self.calls: list[str] = []
        self._fail_on = fail_on_narration
        self._already_failed = False

    async def generate_voiceover(self, text, *, duration_seconds, voice="default"):
        self.calls.append(text)
        if text == self._fail_on and not self._already_failed:
            self._already_failed = True
            raise RuntimeError("simulated transient TTS failure")
        return await super().generate_voiceover(text, duration_seconds=duration_seconds, voice=voice)

PROFILE_PAYLOAD = {
    "name": "Retry Test",
    "niche": {"primary": "mystery", "secondary": []},
    "audience": {"min_age": 18, "max_age": 35, "language": "English"},
    "video": {
        "type": "short",
        "min_duration_seconds": 30,
        "max_duration_seconds": 90,
        "aspect_ratio": "9:16",
        "resolution": "320x568",
    },
    "style": {
        "tone": "mysterious",
        "pacing": "fast",
        "narration": "dramatic",
        "visual_style": "cinematic",
    },
    "strategy": {"hook_types": ["curiosity"]},
    "publishing": {"youtube": True},
    "schedule": {"videos_per_day": 1},
}


def _storyboard_ready_video(client) -> dict:
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 1}
    ).json()
    return client.post("/api/v1/videos/generate", json={"idea_id": ideas[0]["id"]}).json()


def test_retry_after_failure_produces_a_rendered_video(client, db_session):
    video = _storyboard_ready_video(client)

    video_row = db_session.get(Video, video["id"])
    transition(video_row, VideoState.FAILED)
    db_session.commit()

    resp = client.post(f"/api/v1/videos/{video['id']}/retry")
    assert resp.status_code == 200
    assert resp.json()["state"] == "rendered"
    assert resp.json()["rendered_path"]


def test_retry_rejected_when_not_failed(client):
    video = _storyboard_ready_video(client)

    resp = client.post(f"/api/v1/videos/{video['id']}/retry")
    assert resp.status_code == 409


async def test_retry_does_not_regenerate_scenes_that_already_succeeded(client, db_session, monkeypatch):
    """The real concern behind /retry: if scene 2 fails, scene 1's already-
    generated visual (e.g. an established character look) must not be
    thrown away and re-rolled into a different-looking image on retry."""
    from app.models import ContentProfile

    video = _storyboard_ready_video(client)
    video_row = db_session.get(Video, video["id"])
    profile_row = db_session.get(ContentProfile, video_row.content_profile_id)
    assert len(video_row.scenes) >= 2
    second_scene_narration = video_row.scenes[1].narration

    image_provider = _CountingImageProvider()
    tts_provider = _FlakyTTSProvider(fail_on_narration=second_scene_narration)
    monkeypatch.setattr("app.services.production.get_image_provider", lambda: image_provider)
    monkeypatch.setattr("app.services.production.get_tts_provider", lambda: tts_provider)

    with pytest.raises(RuntimeError):
        await produce_video(db_session, video_row, profile_row)
    db_session.refresh(video_row)
    assert video_row.state == VideoState.FAILED
    # scene 2's image generated fine before its TTS call raised -- both
    # scene 1 and scene 2's visuals exist, nothing past scene 2 was reached
    assert image_provider.calls == [
        video_row.scenes[0].visual_prompt,
        video_row.scenes[1].visual_prompt,
    ]

    transition(video_row, VideoState.STORYBOARD_READY)
    db_session.commit()
    await produce_video(db_session, video_row, profile_row)
    db_session.refresh(video_row)

    assert video_row.state == VideoState.RENDERED
    # every scene's visual was generated exactly once across both attempts --
    # scenes 1 and 2 were never re-asked-for on retry
    all_prompts = [scene.visual_prompt for scene in video_row.scenes]
    assert image_provider.calls == all_prompts
    assert len(image_provider.calls) == len(set(image_provider.calls)) == len(video_row.scenes)
