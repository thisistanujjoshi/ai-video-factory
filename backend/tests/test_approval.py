import shutil

import pytest

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

PROFILE_PAYLOAD = {
    "name": "Dark Mysteries",
    "niche": {"primary": "mystery", "secondary": ["unexplained"]},
    "audience": {"min_age": 18, "max_age": 35, "language": "English"},
    "video": {
        "type": "short",
        "min_duration_seconds": 30,
        "max_duration_seconds": 60,
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
    "schedule": {"videos_per_day": 2},
}


def _get_to_awaiting_approval(client) -> dict:
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 2}
    ).json()
    video = client.post("/api/v1/videos/generate", json={"idea_id": ideas[0]["id"]}).json()
    client.post(f"/api/v1/videos/{video['id']}/render")
    report = client.post(f"/api/v1/videos/{video['id']}/qa").json()
    assert report["video"]["state"] == "awaiting_approval"
    return report["video"]


def test_approve_video(client):
    video = _get_to_awaiting_approval(client)
    resp = client.post(f"/api/v1/videos/{video['id']}/approve")
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"

    # can't approve twice
    again = client.post(f"/api/v1/videos/{video['id']}/approve")
    assert again.status_code == 409


def test_reject_video(client):
    video = _get_to_awaiting_approval(client)
    resp = client.post(f"/api/v1/videos/{video['id']}/reject")
    assert resp.status_code == 200
    assert resp.json()["state"] == "rejected"


def test_video_file_download(client):
    video = _get_to_awaiting_approval(client)
    resp = client.get(f"/api/v1/videos/{video['id']}/file")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "video/mp4"
    assert len(resp.content) > 0


def test_video_file_404_when_not_rendered(client):
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 1}
    ).json()
    video = client.post("/api/v1/videos/generate", json={"idea_id": ideas[0]["id"]}).json()
    resp = client.get(f"/api/v1/videos/{video['id']}/file")
    assert resp.status_code == 404
