"""Dependency-free validation tests that run without ChromaDB or Qdrant installed."""

from __future__ import annotations

import pytest

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.embed.embedder import EmbeddingProvider
from react_docs_chunker.indexing.indexer import run_indexing

from _test_utils import make_child, write_jsonl


class TrackingEmbedder(EmbeddingProvider):
    calls = 0

    @property
    def model_id(self) -> str:
        return "tracking"

    @property
    def dimensions(self) -> int:
        return 2

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        self.calls += 1
        return [[0.0, 1.0] for _ in texts]


class RejectingStore:
    def upsert_chunks(self, records, embeddings):
        raise AssertionError("duplicate validation must happen before vector-store upsert")


def test_duplicate_ids_fail_before_embedding_or_upsert(tmp_path):
    path = write_jsonl(tmp_path, [
        make_child("duplicate", "first", sourcePath="a.md"),
        make_child("duplicate", "second", sourcePath="b.md"),
    ])
    embedder = TrackingEmbedder()

    with pytest.raises(ValueError, match="1 duplicate child chunk ID"):
        run_indexing(path, embedder, EmbedCache(tmp_path / "cache.db"), RejectingStore())

    assert embedder.calls == 0
