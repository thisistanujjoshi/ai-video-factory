import pytest

from app.models.video_state import InvalidStateTransition, VideoState, transition


class _FakeVideo:
    def __init__(self, state: VideoState):
        self.state = state


def test_valid_transition_updates_state():
    video = _FakeVideo(VideoState.DRAFT)
    transition(video, VideoState.IDEA_SELECTED)
    assert video.state == VideoState.IDEA_SELECTED


def test_invalid_transition_is_rejected():
    video = _FakeVideo(VideoState.DRAFT)
    with pytest.raises(InvalidStateTransition):
        transition(video, VideoState.PUBLISHED)
    assert video.state == VideoState.DRAFT
