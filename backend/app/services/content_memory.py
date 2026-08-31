# ponytail: picked, not tuned against real embeddings -- the default
# MockEmbeddingProvider is a lexical hashing-trick vector, not a semantic
# one, so this threshold is calibrated for "shares a lot of words," not
# "means the same thing." Revisit once a real embedding provider is live.
SIMILARITY_THRESHOLD = 0.85


def cosine_similarity(a: list[float], b: list[float]) -> float:
    # Providers are required to return unit-normalized vectors (see
    # EmbeddingProvider docstring), so the dot product alone is cosine
    # similarity -- no need to divide by magnitudes here.
    return sum(x * y for x, y in zip(a, b, strict=True))


def is_similar_to_any(embedding: list[float], existing: list[list[float]]) -> bool:
    return any(cosine_similarity(embedding, other) >= SIMILARITY_THRESHOLD for other in existing)
