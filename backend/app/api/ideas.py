from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.ideas import IdeaAgent
from app.database import get_db
from app.models import ContentProfile, ContentStrategy, Idea, ResearchItem
from app.providers.llm import get_llm_provider
from app.schemas.idea import IdeaOut

router = APIRouter(prefix="/ideas", tags=["ideas"])


class IdeaGenerateRequest(BaseModel):
    content_profile_id: int
    research_item_id: int | None = None
    count: int = 20


def _latest_strategy(db: Session, content_profile_id: int) -> ContentStrategy | None:
    return (
        db.query(ContentStrategy)
        .filter_by(content_profile_id=content_profile_id)
        .order_by(ContentStrategy.id.desc())
        .first()
    )


@router.post("/generate", response_model=list[IdeaOut])
async def generate_ideas(payload: IdeaGenerateRequest, db: Session = Depends(get_db)) -> list[Idea]:
    profile = db.get(ContentProfile, payload.content_profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="content profile not found")

    research = None
    if payload.research_item_id is not None:
        research = db.get(ResearchItem, payload.research_item_id)
        if research is None:
            raise HTTPException(status_code=404, detail="research item not found")

    strategy = _latest_strategy(db, profile.id)

    agent = IdeaAgent(get_llm_provider())
    ideas = await agent.generate(db, profile, research, count=payload.count, strategy=strategy)
    db.commit()
    for idea in ideas:
        db.refresh(idea)
    return ideas


@router.get("", response_model=list[IdeaOut])
def list_ideas(content_profile_id: int | None = None, db: Session = Depends(get_db)) -> list[Idea]:
    query = db.query(Idea)
    if content_profile_id is not None:
        query = query.filter(Idea.content_profile_id == content_profile_id)
    return query.order_by(Idea.overall_score.desc()).all()


@router.get("/{idea_id}", response_model=IdeaOut)
def get_idea(idea_id: int, db: Session = Depends(get_db)) -> Idea:
    idea = db.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="idea not found")
    return idea
