from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agents.ideas import IdeaAgent
from app.models import (
    AutomationMode,
    ContentProfile,
    Publication,
    Script,
    Video,
    VideoState,
    transition,
)
from app.providers.llm import get_llm_provider
from app.services.pipeline import generate_video_from_idea
from app.services.production import produce_video
from app.services.publishing import publish_video
from app.services.qa import QA_SCORE_THRESHOLD, QAOutcome, run_qa
from app.services.strategy import latest_strategy

DEFAULT_IDEA_COUNT = 5


class AutomationDisabledError(Exception):
    """Raised when the autonomous cycle is asked to run for a MANUAL profile."""


class NoViableIdeasError(Exception):
    """Raised when every generated idea this cycle was rejected as too
    similar to existing content (spec section 37). Real and expected to
    happen sometimes -- not a bug to route around by reusing a stale idea,
    which would defeat the point of dedup. Caught by the API layer and
    turned into a clean 422, not left to surface as an opaque 500.

    Easy to trigger with the mock LLM specifically: it returns the exact
    same canned ideas every call, so a second cycle on the same profile
    will legitimately reject 100% of them. A real LLM varies its output
    call to call, so this should be rarer in practice -- but still
    possible, hence a real exception type rather than an assumption it
    can't happen.
    """


def can_auto_publish(profile: ContentProfile, outcome: QAOutcome) -> bool:
    """The autonomous-publish gate (spec section 52): AUTONOMOUS mode,
    QA passed, score above threshold, and no content-policy/risk flags.
    Written out explicitly rather than just `outcome.passed` -- this is a
    safety-relevant decision, and each condition should be visible and
    auditable on its own, even though some are implied by the others."""
    return (
        profile.automation_mode == AutomationMode.AUTONOMOUS
        and outcome.technical.passed
        and outcome.content.approved
        and outcome.content.score >= QA_SCORE_THRESHOLD
        and not outcome.content.issues
    )


@dataclass
class AutonomousCycleResult:
    video: Video
    qa_outcome: QAOutcome
    auto_published: bool
    publications: list[Publication] | None


async def run_autonomous_cycle(
    db: Session, profile: ContentProfile, idea_count: int = DEFAULT_IDEA_COUNT
) -> AutonomousCycleResult:
    """Research (skipped -- no ResearchAgent, see Phase 1) -> ideas ->
    production -> QA -> (AUTONOMOUS only) auto-approve + auto-publish.
    Refuses outright for MANUAL profiles; SEMI_AUTOMATIC runs through QA
    and stops, leaving approval to a human via the existing endpoints.
    """
    if profile.automation_mode == AutomationMode.MANUAL:
        raise AutomationDisabledError(
            f"content profile {profile.id} has automation_mode=manual -- autonomous cycle refused"
        )

    strategy = latest_strategy(db, profile.id)
    ideas = await IdeaAgent(get_llm_provider()).generate(
        db, profile, count=idea_count, strategy=strategy
    )
    db.commit()
    if not ideas:
        raise NoViableIdeasError(
            f"content profile {profile.id}: every idea generated this cycle was rejected "
            "as too similar to existing content"
        )
    for idea in ideas:
        db.refresh(idea)
    best_idea = max(ideas, key=lambda i: i.overall_score)

    video = await generate_video_from_idea(db, best_idea, profile)
    await produce_video(db, video, profile)

    script = db.get(Script, video.script_id)
    assert script is not None
    qa_outcome = await run_qa(db, video, script, profile)

    auto_published = False
    publications = None
    if can_auto_publish(profile, qa_outcome):
        transition(video, VideoState.APPROVED)
        db.commit()
        publications = await publish_video(db, video, profile, script)
        auto_published = True

    return AutonomousCycleResult(
        video=video, qa_outcome=qa_outcome, auto_published=auto_published, publications=publications
    )
