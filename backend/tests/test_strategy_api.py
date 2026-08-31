PROFILE_PAYLOAD = {
    "name": "Dark Mysteries",
    "niche": {"primary": "mystery", "secondary": ["unexplained"]},
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
    "publishing": {"youtube": True, "instagram": True, "tiktok": True},
    "schedule": {"videos_per_day": 1},
}


def test_strategy_generate_and_fetch_with_no_history(client):
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]

    generate_resp = client.post(f"/api/v1/content-profiles/{profile_id}/strategy/generate")
    assert generate_resp.status_code == 200
    strategy = generate_resp.json()
    assert strategy["content_profile_id"] == profile_id
    assert strategy["sample_size"] == 0
    assert strategy["best_topics"]  # mock LLM returns a non-empty canned strategy

    fetched = client.get(f"/api/v1/content-profiles/{profile_id}/strategy")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == strategy["id"]


def test_strategy_404_before_any_generation(client):
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    resp = client.get(f"/api/v1/content-profiles/{profile_id}/strategy")
    assert resp.status_code == 404


def test_idea_generation_still_works_after_a_strategy_exists(client):
    """API-level smoke test that the /ideas/generate -> latest-strategy
    wiring doesn't error; the actual prompt-content proof is
    test_strategy_integration.py (unit-level, precise)."""
    profile_id = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD).json()["id"]
    client.post(f"/api/v1/content-profiles/{profile_id}/strategy/generate")

    resp = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 3}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 3
    assert all(idea["overall_score"] > 0 for idea in resp.json())
