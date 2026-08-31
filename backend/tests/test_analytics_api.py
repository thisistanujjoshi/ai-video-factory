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


def _get_to_published(client) -> dict:
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 2}
    ).json()
    video = client.post("/api/v1/videos/generate", json={"idea_id": ideas[0]["id"]}).json()
    client.post(f"/api/v1/videos/{video['id']}/render")
    client.post(f"/api/v1/videos/{video['id']}/qa")
    client.post(f"/api/v1/videos/{video['id']}/approve")
    publish_resp = client.post(f"/api/v1/videos/{video['id']}/publish")
    assert publish_resp.status_code == 200
    return video


def test_collect_and_view_analytics_for_a_published_video(client):
    video = _get_to_published(client)

    collect_resp = client.post(f"/api/v1/videos/{video['id']}/analytics/collect?snapshot_label=1h")
    assert collect_resp.status_code == 200
    metrics = collect_resp.json()
    assert len(metrics) == 3  # youtube, instagram, tiktok
    assert all(m["views"] > 0 for m in metrics)

    per_video = client.get(f"/api/v1/analytics/videos/{video['id']}")
    assert per_video.status_code == 200
    body = per_video.json()
    assert body["video_id"] == video["id"]
    assert len(body["metrics"]) == 3
    assert body["totals"]["views"] == sum(m["views"] for m in metrics)

    overall = client.get("/api/v1/analytics")
    assert overall.status_code == 200
    assert any(row["video_id"] == video["id"] for row in overall.json())


def test_analytics_empty_for_video_with_no_publications(client):
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 1}
    ).json()
    video = client.post("/api/v1/videos/generate", json={"idea_id": ideas[0]["id"]}).json()

    resp = client.get(f"/api/v1/analytics/videos/{video['id']}")
    assert resp.status_code == 200
    assert resp.json()["metrics"] == []
    assert resp.json()["totals"] == {
        "views": 0,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "followers_gained": 0,
    }
