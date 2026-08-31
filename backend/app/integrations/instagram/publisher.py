from datetime import datetime

from app.integrations.base import Publisher, PublishResult
from app.models import PublicationStatus


class InstagramPublisher(Publisher):
    """Instagram Graph API (Reels): two-step publish -- POST
    `/{ig-user-id}/media` with `media_type=REELS` and the video URL to
    create a container, poll the container's `status_code` until
    `FINISHED`, then POST `/{ig-user-id}/media_publish` with the
    container id. No native "schedule for later" on this endpoint; would
    need to be scheduled on our side (a Celery job firing at the target
    time) rather than passed to the API.

    NOT IMPLEMENTED — needs a Facebook Business/App review + a long-lived
    Page access token tied to an Instagram professional account, which
    needs an interactive OAuth consent flow this backend doesn't have a UI
    for yet. `MockPublisher` stands in via `get_publisher()` until this
    exists — see BUILD_STATUS.md Phase 6.
    """

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def publish(self, video, metadata: dict) -> PublishResult:
        raise NotImplementedError("Instagram publishing needs a Page access token flow")

    async def schedule(self, video, metadata: dict, when: datetime) -> PublishResult:
        raise NotImplementedError("Instagram publishing needs a Page access token flow")

    async def get_status(self, platform_ref: str) -> PublicationStatus:
        raise NotImplementedError("Instagram publishing needs a Page access token flow")
