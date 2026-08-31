import shutil
from dataclasses import dataclass

import pytest

from app.models import AutomationMode, ContentProfile
from app.schemas.qa import QAResult
from app.services.autonomous import (
    AutomationDisabledError,
    NoViableIdeasError,
    can_auto_publish,
    run_autonomous_cycle,
)
from app.services.qa import QA_SCORE_THRESHOLD, QAOutcome
from app.video.qa_checks import TechnicalCheckResult

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@dataclass
class _FakeProfile:
    automation_mode: AutomationMode


def _outcome(*, technical_passed=True, approved=True, score=90, issues=None) -> QAOutcome:
    technical = TechnicalCheckResult(
        passed=technical_passed, issues=[] if technical_passed else ["bad"]
    )
    content = QAResult(approved=approved, score=score, issues=issues or [], recommendations=[])
    return QAOutcome(
        passed=technical_passed and approved and score >= QA_SCORE_THRESHOLD,
        technical=technical,
        content=content,
    )


def test_can_auto_publish_requires_autonomous_mode():
    profile = _FakeProfile(AutomationMode.SEMI_AUTOMATIC)
    assert not can_auto_publish(profile, _outcome())


def test_can_auto_publish_true_when_everything_passes():
    profile = _FakeProfile(AutomationMode.AUTONOMOUS)
    assert can_auto_publish(profile, _outcome())


def test_can_auto_publish_false_on_low_score():
    profile = _FakeProfile(AutomationMode.AUTONOMOUS)
    assert not can_auto_publish(profile, _outcome(score=QA_SCORE_THRESHOLD - 1))


def test_can_auto_publish_false_on_technical_failure():
    profile = _FakeProfile(AutomationMode.AUTONOMOUS)
    assert not can_auto_publish(profile, _outcome(technical_passed=False))


def test_can_auto_publish_false_with_content_issues_even_if_approved():
    profile = _FakeProfile(AutomationMode.AUTONOMOUS)
    assert not can_auto_publish(profile, _outcome(issues=["borderline claim"]))


def _make_profile(db_session, mode: AutomationMode, min_d: int, max_d: int) -> ContentProfile:
    profile = ContentProfile(
        name=f"Automation Test {mode.value} {min_d}-{max_d}",
        niche={"primary": "mystery", "secondary": []},
        audience={"min_age": 18, "max_age": 35, "language": "English"},
        video={
            "type": "short",
            "min_duration_seconds": min_d,
            "max_duration_seconds": max_d,
            "aspect_ratio": "9:16",
            "resolution": "320x568",
        },
        style={
            "tone": "mysterious",
            "pacing": "fast",
            "narration": "dramatic",
            "visual_style": "cinematic",
        },
        strategy={"hook_types": ["curiosity"]},
        publishing={"youtube": True, "instagram": False, "tiktok": False},
        schedule={"videos_per_day": 1},
        automation_mode=mode,
    )
    db_session.add(profile)
    db_session.flush()
    return profile


async def test_manual_mode_refuses_to_run(db_session):
    profile = _make_profile(db_session, AutomationMode.MANUAL, 30, 60)
    with pytest.raises(AutomationDisabledError):
        await run_autonomous_cycle(db_session, profile, idea_count=2)


async def test_second_cycle_with_no_new_viable_ideas_raises_clean_error(db_session):
    """Real bug caught via live manual testing: the mock LLM returns the
    exact same canned ideas every call, so a second cycle on the same
    profile legitimately dedups all of them away. Must not surface as an
    unhandled exception -- see NoViableIdeasError's docstring."""
    profile = _make_profile(db_session, AutomationMode.SEMI_AUTOMATIC, 30, 60)
    await run_autonomous_cycle(db_session, profile, idea_count=2)

    with pytest.raises(NoViableIdeasError):
        await run_autonomous_cycle(db_session, profile, idea_count=2)


async def test_semi_automatic_stops_at_awaiting_approval(db_session):
    # 7 mock scenes x 6s = 42s -- bounds that include it so QA passes.
    profile = _make_profile(db_session, AutomationMode.SEMI_AUTOMATIC, 30, 60)

    result = await run_autonomous_cycle(db_session, profile, idea_count=2)

    assert result.video.state.value == "awaiting_approval"
    assert result.qa_outcome.passed is True
    assert result.auto_published is False
    assert result.publications is None


async def test_autonomous_mode_auto_publishes_on_qa_pass(db_session):
    profile = _make_profile(db_session, AutomationMode.AUTONOMOUS, 30, 60)

    result = await run_autonomous_cycle(db_session, profile, idea_count=2)

    assert result.video.state.value == "published"
    assert result.auto_published is True
    assert result.publications is not None
    assert len(result.publications) == 1  # only youtube enabled on this profile
    assert result.publications[0].platform_ref


async def test_autonomous_mode_does_not_auto_publish_on_qa_failure(db_session):
    # bounds exclude the 42s mock render -> technical QA fails
    profile = _make_profile(db_session, AutomationMode.AUTONOMOUS, 45, 75)

    result = await run_autonomous_cycle(db_session, profile, idea_count=2)

    assert result.video.state.value == "qa_failed"
    assert result.auto_published is False
    assert result.publications is None
