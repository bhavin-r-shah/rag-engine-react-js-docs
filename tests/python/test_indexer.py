"""Tests for Phase 2: indexer + ChromaVectorStore."""

from __future__ import annotations

import json

import chromadb
import pytest

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.embed.embedder import EmbeddingProvider
from react_docs_chunker.indexing.indexer import run_indexing
from react_docs_chunker.indexing.vector_store import ChromaVectorStore


# ---------------------------------------------------------------------------
# Stub
# ---------------------------------------------------------------------------

class StubEmbedder(EmbeddingProvider):
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
        # Deterministic: hash of text index drives the vector value
        return [[float(i + 1)] * self.DIMS for i, _ in enumerate(texts)]


def _make_jsonl(tmp_path, records: list[dict]) -> str:
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return str(path)


def _child(chunk_id: str, text: str, parent_id: str = "p1") -> dict:
    return {
        "recordType": "child",
        "chunkId": chunk_id,
        "parentId": parent_id,
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


def _chroma_store(embedder: StubEmbedder) -> ChromaVectorStore:
    return ChromaVectorStore(
        model_id=embedder.model_id,
        dimensions=embedder.dimensions,
        client=chromadb.EphemeralClient(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_upsert_and_dense_query_returns_correct_chunk(tmp_path):
    embedder = StubEmbedder()
    cache = EmbedCache(tmp_path / "cache.db")
    store = _chroma_store(embedder)

    records = [
        _child("c1", "useEffect runs after every render"),
        _child("c2", "useState returns a pair"),
        _child("c3", "useRef persists a mutable value"),
    ]
    jsonl = _make_jsonl(tmp_path, records)

    run_indexing(jsonl, embedder, cache, store)

    # Query with the embedding of "c1" — should come back first
    query_vec = embedder.embed_batch(["useEffect runs after every render"])[0]
    results = store.query_dense(query_vec, n_results=1)

    assert results[0]["chunkId"] == "c1"


def test_rerun_is_idempotent(tmp_path):
    embedder = StubEmbedder()
    cache = EmbedCache(tmp_path / "cache.db")
    store = _chroma_store(embedder)

    records = [_child("c1", "text one"), _child("c2", "text two")]
    jsonl = _make_jsonl(tmp_path, records)

    run_indexing(jsonl, embedder, cache, store)
    run_indexing(jsonl, embedder, cache, store)  # second run — must not duplicate

    results = store.query_dense(embedder.embed_batch(["text one"])[0], n_results=10)
    ids = [r["chunkId"] for r in results]
    assert ids.count("c1") == 1


def test_model_mismatch_raises(tmp_path):
    embedder_a = StubEmbedder("model-a")
    embedder_b = StubEmbedder("model-b")

    client = chromadb.EphemeralClient()
    store_a = ChromaVectorStore(
        model_id=embedder_a.model_id,
        dimensions=embedder_a.dimensions,
        client=client,
        collection_name="test_col",
    )
    store_a.upsert_chunks(
        [_child("c1", "hello")],
        embedder_a.embed_batch(["hello"]),
    )

    with pytest.raises(ValueError, match="model"):
        ChromaVectorStore(
            model_id=embedder_b.model_id,
            dimensions=embedder_b.dimensions,
            client=client,
            collection_name="test_col",
        )


def test_cache_hits_on_second_run(tmp_path):
    embedder = StubEmbedder()
    cache = EmbedCache(tmp_path / "cache.db")
    store = _chroma_store(embedder)

    records = [_child("c1", "some text")]
    jsonl = _make_jsonl(tmp_path, records)

    stats1 = run_indexing(jsonl, embedder, cache, store)
    stats2 = run_indexing(jsonl, embedder, cache, store)

    assert stats1["newly_embedded"] == 1
    assert stats2["cache_hits"] == 1
    assert stats2["newly_embedded"] == 0


def test_dense_query_applies_exact_metadata_filters(tmp_path):
    embedder = StubEmbedder()
    store = _chroma_store(embedder)
    reference = _child("c1", "reference text")
    learn = _child("c2", "learning text")
    reference["docType"] = "reference"
    learn["docType"] = "learn"
    store.upsert_chunks(
        [reference, learn], embedder.embed_batch([reference["text"], learn["text"]])
    )

    results = store.query_dense(
        embedder.embed_batch(["learning text"])[0], n_results=2,
        metadata_filters={"docType": "reference"},
    )

    assert [result["chunkId"] for result in results] == ["c1"]


def test_duplicate_ids_fail_before_embedding(tmp_path):
    embedder = StubEmbedder()
    cache = EmbedCache(tmp_path / "cache.db")
    store = _chroma_store(embedder)
    jsonl = _make_jsonl(
        tmp_path, [_child("duplicate", "first"), _child("duplicate", "second")]
    )

    with pytest.raises(ValueError, match="duplicate child chunk ID"):
        run_indexing(jsonl, embedder, cache, store)

    assert cache.get(embedder.model_id, "first") is None


def test_vector_store_rejects_duplicate_ids_defensively():
    embedder = StubEmbedder()
    store = _chroma_store(embedder)
    records = [_child("duplicate", "first"), _child("duplicate", "second")]

    with pytest.raises(ValueError, match="not unique"):
        store.upsert_chunks(records, embedder.embed_batch(["first", "second"]))
