"""Tests for Phase 3: BM25Store + dense/bm25/hybrid search engine."""

from __future__ import annotations

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.indexing.indexer import run_indexing
from react_docs_chunker.search.bm25 import BM25Store
from react_docs_chunker.search.engine import bm25_search, dense_search, hybrid_search

from _test_utils import StubEmbedder, chroma_store, make_child, write_jsonl


def _setup(tmp_path, embedder, records):
    path = write_jsonl(tmp_path, records)
    cache = EmbedCache(tmp_path / "cache.db")
    store = chroma_store(embedder)
    run_indexing(path, embedder, cache, store)
    bm25 = BM25Store()
    bm25.build(records)
    return path, cache, store, bm25


def test_dense_search_returns_correct_chunk(tmp_path):
    embedder = StubEmbedder()
    records = [
        make_child("c1", "useEffect runs after every render"),
        make_child("c2", "useState returns a stateful pair"),
        make_child("c3", "useRef persists a mutable value"),
    ]
    _, cache, store, _ = _setup(tmp_path, embedder, records)

    # Same text as c1 → same vector → L2 distance 0 → c1 must be first
    results = dense_search("useEffect runs after every render", embedder, cache, store, n=1)
    assert results[0]["chunkId"] == "c1"


def test_user_query_is_embedded_again_for_each_search(tmp_path):
    embedder = StubEmbedder()
    records = [make_child("c1", "useEffect cleanup")]
    _, cache, store, _ = _setup(tmp_path, embedder, records)
    calls_after_offline_index = embedder.call_count

    dense_search("same question", embedder, cache, store, n=1)
    dense_search("same question", embedder, cache, store, n=1)

    assert embedder.call_count == calls_after_offline_index + 2


def test_bm25_search_ranks_exact_match_first(tmp_path):
    embedder = StubEmbedder()
    records = [
        make_child("c1", "useEffect lifecycle hook cleanup function"),
        make_child("c2", "useState manages component state value"),
        make_child("c3", "useRef stores mutable reference object"),
    ]
    _, _, _, bm25 = _setup(tmp_path, embedder, records)

    # "state" appears only in c2 → BM25 must rank c2 first
    results = bm25_search("state", bm25, n=3)
    assert results[0]["chunkId"] == "c2"


def test_hybrid_search_fuses_dense_and_bm25(tmp_path):
    embedder = StubEmbedder()
    records = [
        make_child("c1", "useEffect cleanup runs on unmount phase"),
        make_child("c2", "useState initializes component state value"),
        make_child("c3", "useRef stores a mutable reference object"),
    ]
    _, cache, store, bm25 = _setup(tmp_path, embedder, records)

    # Dense: exact c1 text → L2 distance 0 for c1; BM25: "cleanup" unique to c1 → both agree
    results = hybrid_search(
        "useEffect cleanup runs on unmount phase",
        embedder, cache, store, bm25,
        n=3, rrf_k=60,
    )

    assert results[0]["chunkId"] == "c1"
    assert "rrf_score" in results[0]
    assert len(results) == 3
    # RRF scores must be in descending order
    scores = [r["rrf_score"] for r in results]
    assert scores == sorted(scores, reverse=True)
