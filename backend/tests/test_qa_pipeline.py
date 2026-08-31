import shutil

import pytest

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _profile_payload(min_duration: int, max_duration: int) -> dict:
    return {
        "name": "Dark Mysteries",
        "niche": {"primary": "mystery", "secondary": ["unexplained"]},
        "audience": {"min_age": 18, "max_age": 35, "language": "English"},
        "video": {
            "type": "short",
            "min_duration_seconds": min_duration,
            "max_duration_seconds": max_duration,
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


def _render_to_rendered_state(client, min_duration: int, max_duration: int) -> dict:
    profile_id = client.post(
        "/api/v1/content-profiles", json=_profile_payload(min_duration, max_duration)
    ).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 3}
    ).json()
    best_idea = max(ideas, key=lambda idea: idea["overall_score"])
    video = client.post("/api/v1/videos/generate", json={"idea_id": best_idea["id"]}).json()
    return client.post(f"/api/v1/videos/{video['id']}/render").json()


def test_video_outside_duration_bounds_is_rejected_automatically(client):
    # 7 mock scenes x 6s = 42s; bounds that exclude it force a technical failure.
    rendered = _render_to_rendered_state(client, min_duration=45, max_duration=75)

    report = client.post(f"/api/v1/videos/{rendered['id']}/qa")
    assert report.status_code == 200
    body = report.json()
    assert body["passed"] is False
    assert body["video"]["state"] == "qa_failed"
    assert any("duration" in issue for issue in body["technical_issues"])

    fetched = client.get(f"/api/v1/videos/{rendered['id']}").json()
    assert fetched["state"] == "qa_failed"


def test_video_within_duration_bounds_passes_qa(client):
    rendered = _render_to_rendered_state(client, min_duration=30, max_duration=60)

    report = client.post(f"/api/v1/videos/{rendered['id']}/qa").json()
    assert report["passed"] is True
    assert report["video"]["state"] == "awaiting_approval"
    assert report["content_approved"] is True


def test_qa_before_render_is_rejected(client):
    profile_id = client.post("/api/v1/content-profiles", json=_profile_payload(30, 60)).json()["id"]
    ideas = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 2}
    ).json()
    video = client.post("/api/v1/videos/generate", json={"idea_id": ideas[0]["id"]}).json()

    resp = client.post(f"/api/v1/videos/{video['id']}/qa")
    assert resp.status_code == 409


def test_regenerate_from_qa_failed_produces_a_fresh_storyboard(client):
    rendered = _render_to_rendered_state(client, min_duration=45, max_duration=75)
    client.post(f"/api/v1/videos/{rendered['id']}/qa")

    original_scene_ids = {scene["scene_number"] for scene in rendered["scenes"]}

    regen_resp = client.post(f"/api/v1/videos/{rendered['id']}/regenerate")
    assert regen_resp.status_code == 200
    regenerated = regen_resp.json()
    assert regenerated["state"] == "storyboard_ready"
    assert len(regenerated["scenes"]) > 0
    assert {scene["scene_number"] for scene in regenerated["scenes"]} == original_scene_ids

    # regenerate is only valid from qa_failed
    again = client.post(f"/api/v1/videos/{rendered['id']}/regenerate")
    assert again.status_code == 409
