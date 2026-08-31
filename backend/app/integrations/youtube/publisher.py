from datetime import datetime

from app.integrations.base import Publisher, PublishResult
from app.models import PublicationStatus


class YouTubePublisher(Publisher):
    """YouTube Data API v3: resumable upload via `videos.insert`
    (multipart, `status.privacyStatus`, `snippet.title/description/tags`),
    scheduling via `status.publishAt` + `privacyStatus=private`.

    NOT IMPLEMENTED — needs a per-channel OAuth2 refresh token, which needs
    an interactive user consent flow (`google-auth-oauthlib`) this backend
    doesn't have a UI for yet. `client_id`/`client_secret` alone (from
    `YOUTUBE_CLIENT_ID`/`YOUTUBE_CLIENT_SECRET`) aren't sufficient to
    upload on a user's behalf. `MockPublisher` stands in via
    `get_publisher()` until this exists — see BUILD_STATUS.md Phase 6.
    """

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def publish(self, video, metadata: dict) -> PublishResult:
        raise NotImplementedError("YouTube publishing needs a per-channel OAuth refresh token flow")

    async def schedule(self, video, metadata: dict, when: datetime) -> PublishResult:
        raise NotImplementedError("YouTube publishing needs a per-channel OAuth refresh token flow")

    async def get_status(self, platform_ref: str) -> PublicationStatus:
        raise NotImplementedError("YouTube publishing needs a per-channel OAuth refresh token flow")
