from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents.qa import QAAgent
from app.models import ContentProfile, Script, Video, VideoState, transition
from app.providers.llm import get_llm_provider
from app.schemas.qa import QAResult
from app.video.qa_checks import TechnicalCheckResult, run_technical_checks

# Also the autonomous-mode auto-publish gate later (spec section 52).
QA_SCORE_THRESHOLD = 70


@dataclass
class QAOutcome:
    passed: bool
    technical: TechnicalCheckResult
    content: QAResult


async def run_qa(db: Session, video: Video, script: Script, profile: ContentProfile) -> QAOutcome:
    transition(video, VideoState.QA_PENDING)

    assert video.rendered_path is not None, "run_qa requires a rendered video"
    technical = run_technical_checks(Path(video.rendered_path), profile, video.scenes)
    content = await QAAgent(get_llm_provider()).review(db, video, script, profile)

    passed = technical.passed and content.approved and content.score >= QA_SCORE_THRESHOLD
    transition(video, VideoState.AWAITING_APPROVAL if passed else VideoState.QA_FAILED)
    db.commit()
    db.refresh(video)
    return QAOutcome(passed=passed, technical=technical, content=content)
