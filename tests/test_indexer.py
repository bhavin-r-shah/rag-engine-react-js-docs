"""Tests for Phase 2: indexer + ChromaVectorStore."""

from __future__ import annotations

import chromadb
import pytest

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.indexing.chroma_store import ChromaVectorStore
from react_docs_chunker.indexing.indexer import run_indexing

from _test_utils import StubEmbedder, chroma_store, make_child, write_jsonl


def test_upsert_and_dense_query_returns_correct_chunk(tmp_path):
    embedder = StubEmbedder()
    cache = EmbedCache(tmp_path / "cache.db")
    store = chroma_store(embedder)

    records = [
        make_child("c1", "useEffect runs after every render"),
        make_child("c2", "useState returns a pair"),
        make_child("c3", "useRef persists a mutable value"),
    ]
    jsonl = write_jsonl(tmp_path, records)

    run_indexing(jsonl, embedder, cache, store)

    # Query with the embedding of "c1" — should come back first
    query_vec = embedder.embed_batch(["useEffect runs after every render"])[0]
    results = store.query_dense(query_vec, n_results=1)

    assert results[0]["chunkId"] == "c1"


def test_rerun_is_idempotent(tmp_path):
    embedder = StubEmbedder()
    cache = EmbedCache(tmp_path / "cache.db")
    store = chroma_store(embedder)

    records = [make_child("c1", "text one"), make_child("c2", "text two")]
    jsonl = write_jsonl(tmp_path, records)

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
        [make_child("c1", "hello")],
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
    store = chroma_store(embedder)

    records = [make_child("c1", "some text")]
    jsonl = write_jsonl(tmp_path, records)

    stats1 = run_indexing(jsonl, embedder, cache, store)
    stats2 = run_indexing(jsonl, embedder, cache, store)

    assert stats1["newly_embedded"] == 1
    assert stats2["cache_hits"] == 1
    assert stats2["newly_embedded"] == 0


def test_dense_query_applies_exact_metadata_filters(tmp_path):
    embedder = StubEmbedder()
    store = chroma_store(embedder)
    reference = make_child("c1", "reference text")
    learn = make_child("c2", "learning text", docType="learn")
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
    store = chroma_store(embedder)
    jsonl = write_jsonl(
        tmp_path, [make_child("duplicate", "first"), make_child("duplicate", "second")]
    )

    with pytest.raises(ValueError, match="duplicate child chunk ID"):
        run_indexing(jsonl, embedder, cache, store)

    assert cache.get(embedder.model_id, "first") is None


def test_vector_store_rejects_duplicate_ids_defensively():
    embedder = StubEmbedder()
    store = chroma_store(embedder)
    records = [make_child("duplicate", "first"), make_child("duplicate", "second")]

    with pytest.raises(ValueError, match="not unique"):
        store.upsert_chunks(records, embedder.embed_batch(["first", "second"]))
