from pydantic import BaseModel, ConfigDict


class DurationRecommendation(BaseModel):
    min_seconds: int
    max_seconds: int


class GeneratedStrategy(BaseModel):
    best_topics: list[str]
    best_hook_types: list[str]
    recommended_duration: DurationRecommendation
    recommended_pacing: str
    recommended_posting_windows: list[str]
    avoid_patterns: list[str]
    rationale: str


class ContentStrategyOut(BaseModel):
    id: int
    content_profile_id: int
    best_topics: list[str]
    best_hook_types: list[str]
    recommended_duration: dict
    recommended_pacing: str
    recommended_posting_windows: list[str]
    avoid_patterns: list[str]
    rationale: str
    sample_size: int
    model_config = ConfigDict(from_attributes=True)
