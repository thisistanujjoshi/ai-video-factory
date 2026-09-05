from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.research import ResearchAgent
from app.database import get_db
from app.models import ContentProfile, ResearchItem
from app.providers.llm import get_llm_provider
from app.schemas.research import ResearchItemOut

router = APIRouter(prefix="/research", tags=["research"])


class ResearchGenerateRequest(BaseModel):
    content_profile_id: int
    count: int = 5


@router.post("/generate", response_model=list[ResearchItemOut])
async def generate_research(
    payload: ResearchGenerateRequest, db: Session = Depends(get_db)
) -> list[ResearchItem]:
    profile = db.get(ContentProfile, payload.content_profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="content profile not found")

    agent = ResearchAgent(get_llm_provider())
    items = await agent.generate(db, profile, count=payload.count)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


@router.get("", response_model=list[ResearchItemOut])
def list_research(content_profile_id: int | None = None, db: Session = Depends(get_db)) -> list[ResearchItem]:
    query = db.query(ResearchItem)
    if content_profile_id is not None:
        query = query.filter(ResearchItem.content_profile_id == content_profile_id)
    return query.order_by(ResearchItem.created_at.desc()).all()


@router.get("/{research_item_id}", response_model=ResearchItemOut)
def get_research(research_item_id: int, db: Session = Depends(get_db)) -> ResearchItem:
    item = db.get(ResearchItem, research_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="research item not found")
    return item
