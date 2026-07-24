"""Search functions: dense, BM25, and hybrid RRF fusion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.embed.embedder import EmbeddingProvider

if TYPE_CHECKING:
    from react_docs_chunker.indexing.vector_store import VectorStore
    from react_docs_chunker.search.bm25 import BM25Store


def load_parents(jsonl_path: Path) -> dict[str, dict]:
    parents = {}
    for line in Path(jsonl_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("recordType") == "parent":
            parents[rec["chunkId"]] = rec
    return parents


def embed_query(
    query_text: str, embedder: EmbeddingProvider, cache: EmbedCache
) -> list[float]:
    # Document embeddings are cached during the one-time offline indexing stage.
    # User queries are online inputs and are embedded afresh for every search.
    return embedder.embed_batch([query_text])[0]


def dense_search(
    query_text: str,
    embedder: EmbeddingProvider,
    cache: EmbedCache,
    vector_store: VectorStore,
    n: int = 10,
    metadata_filters: dict[str, str] | None = None,
) -> list[dict]:
    query_vec = embed_query(query_text, embedder, cache)
    return vector_store.query_dense(
        query_vec, n_results=n, metadata_filters=metadata_filters
    )


def bm25_search(query_text: str, bm25_store: BM25Store, n: int = 10) -> list[dict]:
    return bm25_store.query(query_text, n_results=n)


def hybrid_search(
    query_text: str,
    embedder: EmbeddingProvider,
    cache: EmbedCache,
    vector_store: VectorStore,
    bm25_store: BM25Store,
    n: int = 10,
    rrf_k: int = 60,
    metadata_filters: dict[str, str] | None = None,
) -> list[dict]:
    """Combine dense and BM25 results using Reciprocal Rank Fusion (RRF).

    How it works:
      1. Run dense search (vector/semantic) and BM25 (sparse/keyword) independently,
         each fetching n*3 candidates to ensure good coverage before merging.
      2. For every chunk that appears in either result list, compute an RRF score:

             rrf_score = 1 / (rrf_k + rank_dense + 1)
                       + 1 / (rrf_k + rank_bm25 + 1)

         A chunk only in one list still gets the contribution from that list;
         the missing list contributes 0.

      3. Sort all chunks by rrf_score descending and return the top n.

    Why rrf_k=60? The constant softens the reward for rank 0.
    With k=60, rank-0 is worth 1/61 ≈ 0.016 and rank-10 is worth 1/71 ≈ 0.014 —
    a small but meaningful difference. A chunk ranked 1st by both methods beats
    a chunk ranked 1st by only one, which is exactly the desired behaviour.

    Returns list of dicts, each with all fields from the source result plus
    an added 'rrf_score' key.
    """
    candidates = n * 3
    query_vec = embed_query(
        query_text, embedder, cache)
    dense_results = vector_store.query_dense(query_vec, n_results=candidates,
        metadata_filters=metadata_filters,
    )
    bm25_results = bm25_search(query_text, bm25_store, n=candidates)

    scores: dict[str, float] = {}
    chunk_map: dict[str, dict] = {}

    for rank, result in enumerate(dense_results):
        cid = result["chunkId"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
        chunk_map[cid] = result

    for rank, result in enumerate(bm25_results):
        cid = result["chunkId"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
        if cid not in chunk_map:
            chunk_map[cid] = result

    ranked = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    results = []
    for cid in ranked[:n]:
        entry = dict(chunk_map[cid])
        entry["rrf_score"] = scores[cid]
        results.append(entry)
    return results
