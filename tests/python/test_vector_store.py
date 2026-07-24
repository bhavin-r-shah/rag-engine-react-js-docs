"""Tests for Phase 4: QdrantVectorStore dense query and native hybrid search."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest
from qdrant_client import QdrantClient

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.embed.embedder import EmbeddingProvider
from react_docs_chunker.indexing.indexer import run_indexing
from react_docs_chunker.indexing.qdrant_store import QdrantVectorStore


class StubEmbedder(EmbeddingProvider):
    """Text-content deterministic embedder: same text → same vector (SHA-256 based)."""

    DIMS = 4

    def __init__(self, model: str = "stub-model") -> None:
        self._model = model

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self.DIMS

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        result = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            result.append([float(h[i]) / 255.0 for i in range(self.DIMS)])
        return result


class StubSparseEncoder:
    """Deterministic sparse encoder for tests; no model download required."""

    def embed(self, texts):
        for text in texts:
            words = list(dict.fromkeys(text.lower().split()))
            indices = np.array([abs(hash(w)) % 10_000 for w in words], dtype=np.int32)
            values = np.ones(len(words), dtype=np.float32) / max(len(words), 1)
            yield SimpleNamespace(indices=indices, values=values)


def _child(chunk_id: str, text: str) -> dict:
    return {
        "recordType": "child",
        "chunkId": chunk_id,
        "parentId": "p1",
        "text": text,
        "route": "/test",
        "docType": "reference",
        "title": "Test",
        "anchor": "",
        "contentKind": "prose",
        "tokenCount": 10,
        "sourceUrl": "https://example.com/test",
        "sourcePath": "test.md",
    }


def _setup(tmp_path, embedder, records):
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    cache = EmbedCache(tmp_path / "cache.db")
    store = QdrantVectorStore(
        model_id=embedder.model_id,
        dimensions=embedder.dimensions,
        client=QdrantClient(":memory:"),
        collection_name="test_col",
        sparse_encoder=StubSparseEncoder(),
    )
    run_indexing(str(path), embedder, cache, store)
    return str(path), cache, store


def test_qdrant_dense_search_returns_correct_chunk(tmp_path):
    embedder = StubEmbedder()
    records = [
        _child("c1", "useEffect runs after every render"),
        _child("c2", "useState returns a stateful pair"),
        _child("c3", "useRef persists a mutable value"),
    ]
    _, _, store = _setup(tmp_path, embedder, records)

    # Same text as c1 → same SHA-256 vector → cosine similarity 1.0 → c1 must be first
    query_vec = embedder.embed_batch(["useEffect runs after every render"])[0]
    results = store.query_dense(query_vec, n_results=1)
    assert results[0]["chunkId"] == "c1"


def test_qdrant_query_hybrid_returns_results(tmp_path):
    embedder = StubEmbedder()
    records = [
        _child("c1", "useEffect cleanup runs on unmount phase"),
        _child("c2", "useState initializes component state value"),
        _child("c3", "useRef stores a mutable reference object"),
    ]
    _, _, store = _setup(tmp_path, embedder, records)

    # Dense: exact c1 text → cosine 1.0; sparse: "cleanup" unique to c1 → both agree
    query_vec = embedder.embed_batch(["useEffect cleanup runs on unmount phase"])[0]
    results = store.query_hybrid("useEffect cleanup runs on unmount phase", query_vec, n_results=3)

    assert len(results) > 0
    assert all("chunkId" in r for r in results)
    assert all("rrf_score" in r for r in results)
    assert results[0]["chunkId"] == "c1"
