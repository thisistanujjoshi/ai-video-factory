# Weights per spec section 13. Kept as a plain module constant, not a DB
# table or admin-editable setting — nothing consumes a per-profile override
# yet; change here (and bump idea prompt version if the LLM's scoring
# rubric needs to match) when that's actually needed.
IDEA_SCORE_WEIGHTS: dict[str, float] = {
    "curiosity": 0.25,
    "emotion": 0.20,
    "trend": 0.15,
    "novelty": 0.15,
    "shareability": 0.15,
    "production_cost": 0.10,
}


def score_idea(scores: dict[str, int], weights: dict[str, float] = IDEA_SCORE_WEIGHTS) -> float:
    return round(sum(scores[key] * weight for key, weight in weights.items()), 2)
