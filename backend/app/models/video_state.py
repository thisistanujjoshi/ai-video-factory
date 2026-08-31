import enum


class VideoState(str, enum.Enum):
    DRAFT = "draft"
    IDEA_SELECTED = "idea_selected"
    SCRIPT_GENERATING = "script_generating"
    SCRIPT_READY = "script_ready"
    STORYBOARD_GENERATING = "storyboard_generating"
    STORYBOARD_READY = "storyboard_ready"
    ASSETS_GENERATING = "assets_generating"
    ASSETS_READY = "assets_ready"
    RENDERING = "rendering"
    RENDERED = "rendered"
    QA_PENDING = "qa_pending"
    QA_FAILED = "qa_failed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    REJECTED = "rejected"


# ponytail: regeneration paths (QA_FAILED -> back to script/storyboard) are
# guessed at, not yet exercised by any agent — Phase 3 (QA) will confirm/adjust.
VALID_TRANSITIONS: dict[VideoState, set[VideoState]] = {
    VideoState.DRAFT: {VideoState.IDEA_SELECTED, VideoState.FAILED},
    VideoState.IDEA_SELECTED: {VideoState.SCRIPT_GENERATING, VideoState.FAILED},
    VideoState.SCRIPT_GENERATING: {VideoState.SCRIPT_READY, VideoState.FAILED},
    VideoState.SCRIPT_READY: {VideoState.STORYBOARD_GENERATING, VideoState.FAILED},
    VideoState.STORYBOARD_GENERATING: {VideoState.STORYBOARD_READY, VideoState.FAILED},
    VideoState.STORYBOARD_READY: {VideoState.ASSETS_GENERATING, VideoState.FAILED},
    VideoState.ASSETS_GENERATING: {VideoState.ASSETS_READY, VideoState.FAILED},
    VideoState.ASSETS_READY: {VideoState.RENDERING, VideoState.FAILED},
    VideoState.RENDERING: {VideoState.RENDERED, VideoState.FAILED},
    VideoState.RENDERED: {VideoState.QA_PENDING, VideoState.FAILED},
    VideoState.QA_PENDING: {VideoState.AWAITING_APPROVAL, VideoState.QA_FAILED},
    VideoState.QA_FAILED: {
        VideoState.SCRIPT_GENERATING,
        VideoState.STORYBOARD_GENERATING,
        VideoState.REJECTED,
        VideoState.FAILED,
    },
    VideoState.AWAITING_APPROVAL: {VideoState.APPROVED, VideoState.REJECTED},
    VideoState.APPROVED: {VideoState.SCHEDULED, VideoState.PUBLISHING},
    VideoState.SCHEDULED: {VideoState.PUBLISHING, VideoState.FAILED},
    VideoState.PUBLISHING: {VideoState.PUBLISHED, VideoState.FAILED},
    VideoState.PUBLISHED: set(),
    VideoState.FAILED: set(),
    VideoState.REJECTED: set(),
}


class InvalidStateTransition(Exception):
    pass


def transition(video, new_state: VideoState) -> None:
    allowed = VALID_TRANSITIONS.get(video.state, set())
    if new_state not in allowed:
        raise InvalidStateTransition(f"{video.state} -> {new_state} is not a valid transition")
    video.state = new_state
