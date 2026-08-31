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
    "schedule": {"videos_per_day": 1},
}


def _get_to_approved(client) -> dict:
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 2}
    ).json()
    video = client.post("/api/v1/videos/generate", json={"idea_id": ideas[0]["id"]}).json()
    client.post(f"/api/v1/videos/{video['id']}/render")
    client.post(f"/api/v1/videos/{video['id']}/qa")
    approved = client.post(f"/api/v1/videos/{video['id']}/approve")
    assert approved.status_code == 200
    return approved.json()


def test_publish_approved_video_via_api(client):
    video = _get_to_approved(client)

    resp = client.post(f"/api/v1/videos/{video['id']}/publish")
    assert resp.status_code == 200
    publications = resp.json()
    assert {p["platform"] for p in publications} == {"youtube", "instagram", "tiktok"}
    assert all(p["status"] == "published" for p in publications)

    fetched = client.get(f"/api/v1/videos/{video['id']}").json()
    assert fetched["state"] == "published"

    listed = client.get(f"/api/v1/videos/{video['id']}/publications").json()
    assert len(listed) == 3


def test_publish_before_approval_is_rejected(client):
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 1}
    ).json()
    video = client.post("/api/v1/videos/generate", json={"idea_id": ideas[0]["id"]}).json()

    resp = client.post(f"/api/v1/videos/{video['id']}/publish")
    assert resp.status_code == 409


def test_schedule_then_publish_via_api(client):
    video = _get_to_approved(client)

    schedule_resp = client.post(
        f"/api/v1/videos/{video['id']}/schedule", json={"scheduled_for": "2027-01-01T12:00:00Z"}
    )
    assert schedule_resp.status_code == 200
    assert all(p["status"] == "scheduled" for p in schedule_resp.json())

    fetched = client.get(f"/api/v1/videos/{video['id']}").json()
    assert fetched["state"] == "scheduled"

    publish_resp = client.post(f"/api/v1/videos/{video['id']}/publish")
    assert publish_resp.status_code == 200
    assert all(p["status"] == "published" for p in publish_resp.json())
