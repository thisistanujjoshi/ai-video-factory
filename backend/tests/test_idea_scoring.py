from app.services.idea_scoring import score_idea


def test_score_idea_matches_spec_worked_example():
    scores = {
        "curiosity": 91,
        "emotion": 82,
        "trend": 75,
        "novelty": 90,
        "shareability": 87,
        "production_cost": 70,
    }
    assert score_idea(scores) == 83.95
