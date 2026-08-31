from app.providers.embedding import MockEmbeddingProvider
from app.services.content_memory import SIMILARITY_THRESHOLD, cosine_similarity, is_similar_to_any


def test_cosine_similarity_of_identical_vectors_is_one():
    v = [0.6, 0.8]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_of_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


async def test_mock_embedding_flags_near_duplicate_text_as_similar():
    provider = MockEmbeddingProvider()
    a = await provider.embed(
        "The Vanishing Hiker of Blackwood Trail A hiker disappeared without a trace in 1987."
    )
    b = await provider.embed(
        "The Vanishing Hiker of Blackwood Trail A hiker vanished without a trace back in 1987."
    )

    assert cosine_similarity(a, b) >= SIMILARITY_THRESHOLD
    assert is_similar_to_any(a, [b])


async def test_mock_embedding_does_not_flag_unrelated_text():
    provider = MockEmbeddingProvider()
    a = await provider.embed("A hiker vanished on a mountain trail in 1987.")
    b = await provider.embed(
        "Ancient Roman shipwreck found with lost treasure off the coast of Sicily."
    )

    assert cosine_similarity(a, b) < SIMILARITY_THRESHOLD
    assert not is_similar_to_any(a, [b])


def test_is_similar_to_any_empty_existing_list():
    assert not is_similar_to_any([1.0, 0.0], [])
