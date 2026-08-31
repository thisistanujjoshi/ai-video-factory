import shutil

import pytest

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _profile_payload(mode: str, min_d: int, max_d: int) -> dict:
    return {
        "name": f"Automation API Test {mode} {min_d}-{max_d}",
        "niche": {"primary": "mystery", "secondary": []},
        "audience": {"min_age": 18, "max_age": 35, "language": "English"},
        "video": {
            "type": "short",
            "min_duration_seconds": min_d,
            "max_duration_seconds": max_d,
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
        "publishing": {"youtube": True, "instagram": False, "tiktok": False},
        "schedule": {"videos_per_day": 1},
        "automation_mode": mode,
    }


def test_manual_profile_rejects_autonomous_cycle(client):
    profile_id = client.post(
        "/api/v1/content-profiles", json=_profile_payload("manual", 30, 60)
    ).json()["id"]
    resp = client.post(f"/api/v1/content-profiles/{profile_id}/autonomous-cycle")
    assert resp.status_code == 409


def test_semi_automatic_profile_stops_at_approval(client):
    profile_id = client.post(
        "/api/v1/content-profiles", json=_profile_payload("semi_automatic", 30, 60)
    ).json()["id"]

    resp = client.post(f"/api/v1/content-profiles/{profile_id}/autonomous-cycle")
    assert resp.status_code == 200
    body = resp.json()
    assert body["video"]["state"] == "awaiting_approval"
    assert body["auto_published"] is False
    assert body["publications"] == []


def test_second_cycle_with_no_viable_ideas_returns_422_not_500(client):
    profile_id = client.post(
        "/api/v1/content-profiles", json=_profile_payload("semi_automatic", 30, 60)
    ).json()["id"]
    first = client.post(f"/api/v1/content-profiles/{profile_id}/autonomous-cycle")
    assert first.status_code == 200

    second = client.post(f"/api/v1/content-profiles/{profile_id}/autonomous-cycle")
    assert second.status_code == 422


def test_autonomous_profile_auto_publishes(client):
    profile_id = client.post(
        "/api/v1/content-profiles", json=_profile_payload("autonomous", 30, 60)
    ).json()["id"]

    resp = client.post(f"/api/v1/content-profiles/{profile_id}/autonomous-cycle")
    assert resp.status_code == 200
    body = resp.json()
    assert body["video"]["state"] == "published"
    assert body["auto_published"] is True
    assert len(body["publications"]) == 1
    assert body["publications"][0]["platform"] == "youtube"

    # the video really is fetchable/playable afterward, same as a manual publish
    fetched = client.get(f"/api/v1/videos/{body['video']['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["state"] == "published"


def test_default_automation_mode_is_manual(client):
    payload = _profile_payload("manual", 30, 60)
    del payload["automation_mode"]
    profile_id = client.post("/api/v1/content-profiles", json=payload).json()["id"]

    resp = client.post(f"/api/v1/content-profiles/{profile_id}/autonomous-cycle")
    assert resp.status_code == 409  # safety default: new profiles don't auto-run
