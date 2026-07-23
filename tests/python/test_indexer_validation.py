"""Dependency-free validation tests that run without ChromaDB installed."""

import json

import pytest

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.embed.embedder import EmbeddingProvider
from react_docs_chunker.indexing.indexer import run_indexing


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
    path = tmp_path / "chunks.jsonl"
    records = [
        {"recordType": "child", "chunkId": "duplicate", "text": "first", "sourcePath": "a.md"},
        {"recordType": "child", "chunkId": "duplicate", "text": "second", "sourcePath": "b.md"},
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    embedder = TrackingEmbedder()

    with pytest.raises(ValueError, match="1 duplicate child chunk ID"):
        run_indexing(path, embedder, EmbedCache(tmp_path / "cache.db"), RejectingStore())

    assert embedder.calls == 0
