import hashlib
import math
import re
from abc import ABC, abstractmethod

from app.config import get_settings

# 256 was too small: two single-digit tokens (e.g. "2" and "4" in
# otherwise-identical mock idea text) could hash into the same bucket and
# produce a false 1.0 similarity. 4096 keeps that collision rate low even
# across a few dozen short, mostly-boilerplate mock idea batches.
EMBEDDING_DIM = 4096


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Return a fixed-length vector for `text`. Callers compare vectors
        with cosine similarity (app/services/content_memory.py), so
        implementations should return unit-normalized vectors."""


def _hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    vector = [0.0] * dim
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        index = int(hashlib.md5(token.encode()).hexdigest(), 16) % dim
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class MockEmbeddingProvider(EmbeddingProvider):
    """The 'hashing trick': a bag-of-words vector where each token hashes
    to a dimension. Not a semantic embedding (no notion that "detective"
    and "investigator" are related) -- but it's deterministic, needs no
    API call, and genuinely captures lexical overlap, which is exactly
    what near-duplicate title/premise detection needs (spec section 37).
    """

    async def embed(self, text: str) -> list[float]:
        return _hash_embedding(text)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google's embedding model via `google-genai`.

    IMPLEMENTED — NOT LIVE TESTED: verified the SDK call shape
    (`client.aio.models.embed_content(...) -> response.embeddings[0].values`)
    by inspecting the installed SDK, but didn't spend further live-API
    budget on this pass's key (see BUILD_STATUS.md Phase 5/8). Re-verify
    the model name via `client.models.list()` before relying on it — Phase
    5 already hit one real model-name deprecation on this account.
    """

    model_name = "gemini-embedding-001"

    def __init__(self, api_key: str, model: str | None = None):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        if model:
            self.model_name = model

    async def embed(self, text: str) -> list[float]:
        response = await self._client.aio.models.embed_content(model=self.model_name, contents=text)
        embeddings = response.embeddings or []
        if not embeddings or embeddings[0].values is None:
            raise RuntimeError("Gemini returned no embedding for this text")
        return list(embeddings[0].values)


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.embedding_provider or "mock"
    if provider == "mock":
        return MockEmbeddingProvider()
    if provider == "gemini":
        if not settings.embedding_api_key:
            raise ValueError("EMBEDDING_API_KEY is required when EMBEDDING_PROVIDER=gemini")
        return GeminiEmbeddingProvider(settings.embedding_api_key)
    raise ValueError(
        f"embedding provider {provider!r} is not implemented (mock, gemini are available)"
    )
