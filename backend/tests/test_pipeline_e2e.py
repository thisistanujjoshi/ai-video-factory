PROFILE_PAYLOAD = {
    "name": "Dark Mysteries",
    "niche": {"primary": "mystery", "secondary": ["unexplained"]},
    "audience": {"min_age": 18, "max_age": 35, "language": "English"},
    "video": {
        "type": "short",
        "min_duration_seconds": 45,
        "max_duration_seconds": 75,
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
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


def test_content_profile_produces_a_structured_storyboard(client):
    profile_resp = client.post("/api/v1/content-profiles", json=PROFILE_PAYLOAD)
    assert profile_resp.status_code == 201
    profile_id = profile_resp.json()["id"]

    ideas_resp = client.post(
        "/api/v1/ideas/generate", json={"content_profile_id": profile_id, "count": 5}
    )
    assert ideas_resp.status_code == 200
    ideas = ideas_resp.json()
    assert len(ideas) == 5
    best_idea = max(ideas, key=lambda idea: idea["overall_score"])

    video_resp = client.post("/api/v1/videos/generate", json={"idea_id": best_idea["id"]})
    assert video_resp.status_code == 201
    video = video_resp.json()

    assert video["state"] == "storyboard_ready"
    assert video["idea_id"] == best_idea["id"]
    assert len(video["scenes"]) > 0
    for scene in video["scenes"]:
        assert scene["visual_prompt"]
        assert scene["camera_motion"]

    fetched = client.get(f"/api/v1/videos/{video['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["state"] == "storyboard_ready"
