import shutil

import pytest

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

PROFILE_PAYLOAD = {
    "name": "Video Provider Test",
    "niche": {"primary": "mystery", "secondary": ["unexplained"]},
    "audience": {"min_age": 18, "max_age": 35, "language": "English"},
    "video": {
        "type": "short",
        "min_duration_seconds": 10,
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
    "publishing": {"youtube": True, "instagram": True, "tiktok": True},
    "schedule": {"videos_per_day": 1},
}


def test_render_uses_generated_video_clips_when_video_provider_configured(client, monkeypatch):
    monkeypatch.setenv("VIDEO_PROVIDER", "mock")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
        ideas = client.post(
            "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 2}
        ).json()
        video = client.post("/api/v1/videos/generate", json={"idea_id": ideas[0]["id"]}).json()

        render_resp = client.post(f"/api/v1/videos/{video['id']}/render")
        assert render_resp.status_code == 200
        rendered = render_resp.json()
        assert rendered["state"] == "rendered"
        assert rendered["rendered_path"]
    finally:
        get_settings.cache_clear()
