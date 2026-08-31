import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

PROFILE_PAYLOAD = {
    "name": "Dark Mysteries",
    "niche": {"primary": "mystery", "secondary": ["unexplained"]},
    "audience": {"min_age": 18, "max_age": 35, "language": "English"},
    "video": {
        "type": "short",
        "min_duration_seconds": 45,
        "max_duration_seconds": 75,
        "aspect_ratio": "9:16",
        "resolution": "320x568",
    },
    "style": {
        "tone": "mysterious",
        "pacing": "fast",
        "narration": "dramatic",
        "visual_style": "cinematic",
    },
    "strategy": {"hook_types": ["curiosity", "question"]},
    "publishing": {"youtube": True, "instagram": True, "tiktok": True},
    "schedule": {"videos_per_day": 2},
}


def test_storyboard_produces_a_real_mp4(client):
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 3}
    ).json()
    best_idea = max(ideas, key=lambda idea: idea["overall_score"])

    video = client.post("/api/v1/videos/generate", json={"idea_id": best_idea["id"]}).json()
    assert video["state"] == "storyboard_ready"
    scene_count = len(video["scenes"])

    render_resp = client.post(f"/api/v1/videos/{video['id']}/render")
    assert render_resp.status_code == 200
    rendered = render_resp.json()
    assert rendered["state"] == "rendered"
    assert rendered["rendered_path"]

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1",
            rendered["rendered_path"],
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "codec_type=video" in probe.stdout
    assert "codec_type=audio" in probe.stdout

    fetched = client.get(f"/api/v1/videos/{video['id']}").json()
    assert fetched["state"] == "rendered"

    # rendering twice from a non-storyboard_ready state is rejected
    second = client.post(f"/api/v1/videos/{video['id']}/render")
    assert second.status_code == 409
    assert scene_count > 0
