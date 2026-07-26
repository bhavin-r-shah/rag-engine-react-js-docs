"""Tests for Phase 4: QdrantVectorStore dense query and native hybrid search."""

from __future__ import annotations

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.indexing.indexer import run_indexing

from _test_utils import StubEmbedder, make_child, qdrant_store, write_jsonl


def _setup(tmp_path, embedder, records):
    path = write_jsonl(tmp_path, records)
    cache = EmbedCache(tmp_path / "cache.db")
    store = qdrant_store(embedder, collection_name="test_col")
    run_indexing(path, embedder, cache, store)
    return path, cache, store


def test_qdrant_dense_search_returns_correct_chunk(tmp_path):
    embedder = StubEmbedder()
    records = [
        make_child("c1", "useEffect runs after every render"),
        make_child("c2", "useState returns a stateful pair"),
        make_child("c3", "useRef persists a mutable value"),
    ]
    _, _, store = _setup(tmp_path, embedder, records)

    # Same text as c1 → same SHA-256 vector → cosine similarity 1.0 → c1 must be first
    query_vec = embedder.embed_batch(["useEffect runs after every render"])[0]
    results = store.query_dense(query_vec, n_results=1)
    assert results[0]["chunkId"] == "c1"


def test_qdrant_query_hybrid_returns_results(tmp_path):
    embedder = StubEmbedder()
    records = [
        make_child("c1", "useEffect cleanup runs on unmount phase"),
        make_child("c2", "useState initializes component state value"),
        make_child("c3", "useRef stores a mutable reference object"),
    ]
    _, _, store = _setup(tmp_path, embedder, records)

    # Dense: exact c1 text → cosine 1.0; sparse: "cleanup" unique to c1 → both agree
    query_vec = embedder.embed_batch(["useEffect cleanup runs on unmount phase"])[0]
    results = store.query_hybrid("useEffect cleanup runs on unmount phase", query_vec, n_results=3)

    assert len(results) > 0
    assert all("chunkId" in r for r in results)
    assert all("rrf_score" in r for r in results)
    assert results[0]["chunkId"] == "c1"
