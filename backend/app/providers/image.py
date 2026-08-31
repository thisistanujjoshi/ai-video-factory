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


def get_image_provider() -> ImageProvider:
    provider = get_settings().image_provider or "mock"
    if provider == "mock":
        return MockImageProvider()
    raise ValueError(
        f"image provider {provider!r} is not implemented yet (real providers land in Phase 5)"
    )
