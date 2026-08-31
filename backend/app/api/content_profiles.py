from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.strategy import StrategyAgent
from app.database import get_db
from app.models import ContentProfile, ContentStrategy
from app.providers.llm import get_llm_provider
from app.schemas.content_profile import ContentProfileCreate, ContentProfileOut
from app.schemas.strategy import ContentStrategyOut
from app.services.strategy import compute_patterns

router = APIRouter(prefix="/content-profiles", tags=["content-profiles"])


def _apply(profile: ContentProfile, payload: ContentProfileCreate) -> None:
    profile.name = payload.name
    profile.niche = payload.niche.model_dump()
    profile.audience = payload.audience.model_dump()
    profile.video = payload.video.model_dump()
    profile.style = payload.style.model_dump()
    profile.strategy = payload.strategy.model_dump()
    profile.publishing = payload.publishing.model_dump()
    profile.schedule = payload.schedule.model_dump()


@router.post("", response_model=ContentProfileOut, status_code=201)
def create_profile(payload: ContentProfileCreate, db: Session = Depends(get_db)) -> ContentProfile:
    profile = ContentProfile()
    _apply(profile, payload)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=list[ContentProfileOut])
def list_profiles(db: Session = Depends(get_db)) -> list[ContentProfile]:
    return db.query(ContentProfile).order_by(ContentProfile.id).all()


@router.get("/{profile_id}", response_model=ContentProfileOut)
def get_profile(profile_id: int, db: Session = Depends(get_db)) -> ContentProfile:
    profile = db.get(ContentProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="content profile not found")
    return profile


@router.put("/{profile_id}", response_model=ContentProfileOut)
def update_profile(
    profile_id: int, payload: ContentProfileCreate, db: Session = Depends(get_db)
) -> ContentProfile:
    profile = db.get(ContentProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="content profile not found")
    _apply(profile, payload)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)) -> None:
    profile = db.get(ContentProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="content profile not found")
    db.delete(profile)
    db.commit()


@router.post("/{profile_id}/strategy/generate", response_model=ContentStrategyOut)
async def generate_strategy(profile_id: int, db: Session = Depends(get_db)) -> ContentStrategy:
    profile = db.get(ContentProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="content profile not found")

    patterns = compute_patterns(db, profile_id)
    generated = await StrategyAgent(get_llm_provider()).generate(db, profile, patterns)

    strategy = ContentStrategy(
        content_profile_id=profile_id,
        best_topics=generated.best_topics,
        best_hook_types=generated.best_hook_types,
        recommended_duration=generated.recommended_duration.model_dump(),
        recommended_pacing=generated.recommended_pacing,
        recommended_posting_windows=generated.recommended_posting_windows,
        avoid_patterns=generated.avoid_patterns,
        rationale=generated.rationale,
        sample_size=patterns["sample_size"],
        patterns=patterns,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.get("/{profile_id}/strategy", response_model=ContentStrategyOut)
def get_latest_strategy(profile_id: int, db: Session = Depends(get_db)) -> ContentStrategy:
    strategy = (
        db.query(ContentStrategy)
        .filter_by(content_profile_id=profile_id)
        .order_by(ContentStrategy.id.desc())
        .first()
    )
    if strategy is None:
        raise HTTPException(status_code=404, detail="no strategy generated yet for this profile")
    return strategy
