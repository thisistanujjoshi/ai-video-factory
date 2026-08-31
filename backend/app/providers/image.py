import asyncio
import hashlib
from abc import ABC, abstractmethod

from app.config import get_settings


class ImageProvider(ABC):
    @abstractmethod
    async def generate_image(self, prompt: str, *, width: int = 1080, height: int = 1920) -> bytes:
        """Return raw PNG bytes for one still image matching `prompt`."""


def _color_from_prompt(prompt: str) -> str:
    digest = hashlib.sha256(prompt.encode()).hexdigest()
    return f"0x{digest[:6]}"


class MockImageProvider(ImageProvider):
    """A solid-color PNG, colored deterministically from the prompt text, via
    ffmpeg's lavfi color source -- no image-gen API key, no new dependency
    (ffmpeg is already required for rendering)."""

    async def generate_image(self, prompt: str, *, width: int = 1080, height: int = 1920) -> bytes:
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
            f"color=c={color}:s={width}x{height}:d=1",
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed generating mock image: {stderr.decode()}")
        return stdout


class GeminiImageProvider(ImageProvider):
    """Google Gemini image generation via `google-genai`.

    IMPLEMENTED — NOT LIVE TESTED: the available API key returned a real
    429 (`RESOURCE_EXHAUSTED`, free-tier image quota is 0 for every image
    model) on 2026-08-31 -- a confirmed account limitation, not a guess.
    The LLM path on this same key (`GeminiLLMProvider`) is verified live.

    ponytail: doesn't request a specific output resolution -- the
    `generate_content` image API doesn't take width/height the way the mock
    (or DALL-E-style APIs) do. The renderer already scales every scene
    image to the profile's target resolution (`app/video/renderer.py`), so
    this is fine as long as that scale step tolerates a differently-aspect
    source image; revisit (crop/pad instead of stretch) once this path is
    actually live-tested against real output.
    """

    model_name = "gemini-3.1-flash-image"

    def __init__(self, api_key: str, model: str | None = None):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        if model:
            self.model_name = model

    async def generate_image(self, prompt: str, *, width: int = 1080, height: int = 1920) -> bytes:
        response = await self._client.aio.models.generate_content(
            model=self.model_name, contents=prompt
        )
        candidates = response.candidates or []
        content = candidates[0].content if candidates else None
        for part in content.parts or [] if content else []:
            if part.inline_data is not None and part.inline_data.data is not None:
                return part.inline_data.data
        raise RuntimeError("Gemini returned no image data for this prompt")


def get_image_provider() -> ImageProvider:
    settings = get_settings()
    provider = settings.image_provider or "mock"
    if provider == "mock":
        return MockImageProvider()
    if provider == "gemini":
        if not settings.image_api_key:
            raise ValueError("IMAGE_API_KEY is required when IMAGE_PROVIDER=gemini")
        return GeminiImageProvider(settings.image_api_key)
    raise ValueError(f"image provider {provider!r} is not implemented (mock, gemini are available)")
