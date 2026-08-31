from app.integrations.base import MockPublisher, Publisher, PublishError, PublishResult

PLATFORMS = ("youtube", "instagram", "tiktok")


def get_publisher(platform: str) -> Publisher:
    """Real per-platform publishers exist (YouTubePublisher etc.) but each
    needs an OAuth consent flow this backend doesn't have a UI for yet
    (see their docstrings) -- MockPublisher stands in for every platform
    until then. Swap the branch here in once one is wired up."""
    if platform not in PLATFORMS:
        raise ValueError(f"unknown platform {platform!r}")
    return MockPublisher(platform)


__all__ = [
    "PLATFORMS",
    "MockPublisher",
    "PublishError",
    "PublishResult",
    "Publisher",
    "get_publisher",
]
