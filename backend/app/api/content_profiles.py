from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ContentProfile
from app.schemas.content_profile import ContentProfileCreate, ContentProfileOut

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
