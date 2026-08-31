import asyncio
import hashlib
from abc import ABC, abstractmethod

from app.config import get_settings


class VideoProvider(ABC):
    """Generates an actual motion video clip per scene, as an alternative
    to ImageProvider's still frame. Optional: unconfigured (the default)
    means the pipeline uses ImageProvider instead, exactly as before this
    provider existed -- see get_video_provider()."""

    @abstractmethod
    async def generate_video_clip(
        self, prompt: str, *, duration_seconds: float, width: int = 1080, height: int = 1920
    ) -> bytes:
        """Return raw video bytes (MP4) for one scene matching `prompt`."""


def _color_from_prompt(prompt: str) -> str:
    digest = hashlib.sha256(prompt.encode()).hexdigest()
    return f"0x{digest[:6]}"


class MockVideoProvider(VideoProvider):
    """A color that cycles smoothly over the clip's duration, deterministic
    from the prompt -- via ffmpeg's lavfi `color` source + a `hue` rotation,
    same no-API-key/no-new-dependency approach as the other mocks. Visibly
    in motion (unlike MockImageProvider's still frame), which is the one
    thing that actually needs to differ to exercise the video-clip code
    path in the renderer, without pretending to be AI-generated content."""

    async def generate_video_clip(
        self, prompt: str, *, duration_seconds: float, width: int = 1080, height: int = 1920
    ) -> bytes:
        duration = max(duration_seconds, 0.1)
        color = _color_from_prompt(prompt)
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={width}x{height}:d={duration}",
            "-vf",
            f"hue=H=2*PI*t/{duration},format=yuv420p",
            "-c:v",
            "libopenh264",
            "-f",
            "mp4",
            "-movflags",
            "frag_keyframe+empty_moov",
            "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed generating mock video clip: {stderr.decode()}")
        return stdout


class GeminiVideoError(RuntimeError):
    pass


class GeminiVideoProvider(VideoProvider):
    """Google Veo via `google-genai`.

    IMPLEMENTED — NOT LIVE TESTED: a real call (`veo-3.1-lite-generate-preview`,
    4s clip) returned a real 429 (`RESOURCE_EXHAUSTED`, no quota detail —
    unlike the TTS provider's explicit "limit: 10/day" this one gave no
    number, consistent with Veo typically being paid/billing-gated rather
    than free-tier-with-a-quota) on 2026-08-31. The operation-polling shape
    below (`generate_videos` -> `GenerateVideosOperation` -> poll via
    `operations.get` -> `response.generated_videos[0].video.video_bytes`)
    is verified against the installed SDK's type signatures, not against a
    real completed response — re-verify the result-extraction path
    (`video_bytes` vs. `uri`-only) once a working account is available.

    A real generation is a long-running operation (commonly reported in the
    minutes, not seconds) -- calling this from a synchronous request
    handler the way the rest of this pipeline's providers are called will
    likely time out in practice. Nothing about that is solved here; see
    BUILD_STATUS.md.
    """

    model_name = "veo-3.1-lite-generate-preview"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        poll_interval_seconds: float = 10.0,
        max_wait_seconds: float = 600.0,
    ):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        if model:
            self.model_name = model
        self.poll_interval_seconds = poll_interval_seconds
        self.max_wait_seconds = max_wait_seconds

    async def generate_video_clip(
        self, prompt: str, *, duration_seconds: float, width: int = 1080, height: int = 1920
    ) -> bytes:
        from google.genai import types

        aspect_ratio = "9:16" if height >= width else "16:9"
        operation = await self._client.aio.models.generate_videos(
            model=self.model_name,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                duration_seconds=max(round(duration_seconds), 1),
                number_of_videos=1,
            ),
        )

        waited = 0.0
        while not operation.done:
            if waited >= self.max_wait_seconds:
                raise GeminiVideoError(
                    f"Veo generation did not finish within {self.max_wait_seconds}s"
                )
            await asyncio.sleep(self.poll_interval_seconds)
            waited += self.poll_interval_seconds
            operation = await self._client.aio.operations.get(operation)

        if operation.error:
            raise GeminiVideoError(f"Veo generation failed: {operation.error}")

        videos = operation.response.generated_videos if operation.response else None
        if not videos:
            raise GeminiVideoError("Veo returned no video for this prompt")

        video = videos[0].video
        if video is None:
            raise GeminiVideoError("Veo returned an empty video entry for this prompt")
        if video.video_bytes is not None:
            return video.video_bytes
        if video.uri:
            raise GeminiVideoError(
                f"Veo returned a URI ({video.uri}) instead of inline bytes -- "
                "downloading from a GCS URI isn't implemented"
            )
        raise GeminiVideoError("Veo returned a video with neither inline bytes nor a URI")


def get_video_provider() -> VideoProvider | None:
    """None means "not configured" -- the pipeline falls back to
    ImageProvider (still frames), exactly the behavior before this
    provider existed. Explicit opt-in via VIDEO_PROVIDER=mock or =gemini."""
    settings = get_settings()
    provider = settings.video_provider or None
    if provider is None:
        return None
    if provider == "mock":
        return MockVideoProvider()
    if provider == "gemini":
        if not settings.video_api_key:
            raise ValueError("VIDEO_API_KEY is required when VIDEO_PROVIDER=gemini")
        return GeminiVideoProvider(settings.video_api_key)
    raise ValueError(f"video provider {provider!r} is not implemented (mock, gemini are available)")
