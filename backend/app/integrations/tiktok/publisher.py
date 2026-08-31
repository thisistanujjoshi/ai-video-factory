from datetime import datetime

from app.integrations.base import Publisher, PublishResult
from app.models import PublicationStatus


class TikTokPublisher(Publisher):
    """TikTok Content Posting API: POST `/v2/post/publish/video/init/`
    with `post_info` (caption, privacy level) and `source_info` to start a
    chunked upload session, PUT the video bytes to the returned upload
    URL, then poll `/v2/post/publish/status/fetch/` for completion.

    NOT IMPLEMENTED — needs an approved TikTok developer app plus a
    per-creator OAuth2 access token, which needs an interactive consent
    flow this backend doesn't have a UI for yet. `MockPublisher` stands in
    via `get_publisher()` until this exists — see BUILD_STATUS.md Phase 6.
    """

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def publish(self, video, metadata: dict) -> PublishResult:
        raise NotImplementedError("TikTok publishing needs a per-creator OAuth access token flow")

    async def schedule(self, video, metadata: dict, when: datetime) -> PublishResult:
        raise NotImplementedError("TikTok publishing needs a per-creator OAuth access token flow")

    async def get_status(self, platform_ref: str) -> PublicationStatus:
        raise NotImplementedError("TikTok publishing needs a per-creator OAuth access token flow")
