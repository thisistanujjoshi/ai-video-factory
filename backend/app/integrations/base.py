import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.models import PublicationStatus


class PublishError(Exception):
    """Raised for a failed publish/schedule attempt. Treated as transient by
    the retry loop in app/services/publishing.py -- there's no real-provider
    error taxonomy yet to distinguish transient from permanent (spec section
    41); add one once a real Publisher exists to observe actual failures."""


@dataclass
class PublishResult:
    platform_ref: str
    status: PublicationStatus
    raw: dict = field(default_factory=dict)


class Publisher(ABC):
    """One implementation per platform. Never called directly by video-
    generation code -- see app/services/publishing.py."""

    @abstractmethod
    async def publish(self, video, metadata: dict) -> PublishResult: ...

    @abstractmethod
    async def schedule(self, video, metadata: dict, when: datetime) -> PublishResult: ...

    @abstractmethod
    async def get_status(self, platform_ref: str) -> PublicationStatus: ...


class MockPublisher(Publisher):
    """Simulates a platform for local dev/tests -- no OAuth, no network.

    `fail_times` lets a test force N transient failures before success, to
    exercise the retry path in app/services/publishing.py without needing a
    real flaky API.
    """

    def __init__(self, platform: str, fail_times: int = 0):
        self.platform = platform
        self._fail_times = fail_times
        self._attempts = 0

    async def publish(self, video, metadata: dict) -> PublishResult:
        self._attempts += 1
        if self._attempts <= self._fail_times:
            raise PublishError(f"mock transient failure ({self._attempts}/{self._fail_times})")
        return PublishResult(
            platform_ref=f"mock-{self.platform}-{video.id}-{uuid.uuid4().hex[:8]}",
            status=PublicationStatus.PUBLISHED,
            raw={"mock": True, "metadata": metadata},
        )

    async def schedule(self, video, metadata: dict, when: datetime) -> PublishResult:
        return PublishResult(
            platform_ref=f"mock-{self.platform}-{video.id}-scheduled",
            status=PublicationStatus.SCHEDULED,
            raw={"mock": True, "scheduled_for": when.isoformat()},
        )

    async def get_status(self, platform_ref: str) -> PublicationStatus:
        return PublicationStatus.PUBLISHED
