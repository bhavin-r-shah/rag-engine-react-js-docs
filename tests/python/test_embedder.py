"""Tests for the embedding layer (Phase 1).

Uses a stub embedder so no model is downloaded during CI.
"""

import pytest

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.embed.embedder import EmbeddingProvider



# ---------------------------------------------------------------------------
# Stub
# ---------------------------------------------------------------------------


class StubEmbedder(EmbeddingProvider):
    """Returns deterministic fake vectors; call count is tracked."""

    DIMS = 4

    def __init__(self) -> None:
        self.call_count = 0

    @property
    def model_id(self) -> str:
        return "stub-model"

    @property
    def dimensions(self) -> int:
        return self.DIMS

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        self.call_count += 1
        # Each vector is just [i, i, i, i] where i = index in the batch.
        return [[float(i)] * self.DIMS for i in range(len(texts))]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_embed_batch_returns_correct_shape():
    embedder = StubEmbedder()
    texts = ["hello", "world", "foo"]
    vectors = embedder.embed_batch(texts)

    assert len(vectors) == len(texts)
    assert all(len(v) == StubEmbedder.DIMS for v in vectors)


def test_cache_miss_calls_embedder_and_stores(tmp_path):
    embedder = StubEmbedder()
    cache = EmbedCache(tmp_path / "test.db")

    text = "react hooks"
    assert cache.get(embedder.model_id, text) is None  # cold cache

    vector = embedder.embed_batch([text])[0]
    cache.put(embedder.model_id, text, vector)

    stored = cache.get(embedder.model_id, text)
    assert stored == vector
    assert embedder.call_count == 1


def test_cache_hit_returns_same_vector_without_re_embedding(tmp_path):
    embedder = StubEmbedder()
    cache = EmbedCache(tmp_path / "test.db")

    text = "react hooks"
    vector = embedder.embed_batch([text])[0]
    cache.put(embedder.model_id, text, vector)

    calls_before = embedder.call_count

    # Simulate a warm-cache lookup: get from cache, don't call embedder.
    cached = cache.get(embedder.model_id, text)
    assert cached == vector
    assert embedder.call_count == calls_before  # embedder NOT called again


def test_cache_key_is_model_scoped(tmp_path):
    """Same text with different model IDs should be stored independently."""
    embedder_a = StubEmbedder()
    embedder_b = StubEmbedder()
    # Give embedder_b a different model_id via subclassing
    embedder_b._model_id = "other-model"

    class _OtherStub(StubEmbedder):
        @property
        def model_id(self) -> str:
            return "other-model"

    embedder_b = _OtherStub()
    cache = EmbedCache(tmp_path / "test.db")

    text = "shared text"
    vec_a = [1.0, 2.0, 3.0, 4.0]
    vec_b = [9.0, 8.0, 7.0, 6.0]

    cache.put(embedder_a.model_id, text, vec_a)
    cache.put(embedder_b.model_id, text, vec_b)

    assert cache.get(embedder_a.model_id, text) == vec_a
    assert cache.get(embedder_b.model_id, text) == vec_b
