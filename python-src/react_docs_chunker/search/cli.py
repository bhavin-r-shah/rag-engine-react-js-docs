"""CLI entry point: search React docs using dense, BM25, or hybrid search.

Usage:
    python -m react_docs_chunker.search.cli QUERY [--mode {dense,bm25,hybrid,all}]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from react_docs_chunker._cli_utils import build_embedder, build_vector_store
from react_docs_chunker.config import EMBED_CACHE_PATH, JSONL_PATH
from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.search.bm25 import BM25Store
from react_docs_chunker.search.engine import bm25_search, dense_search, embed_query, hybrid_search


def _load_children(jsonl_path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(jsonl_path).read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("recordType") == "child"
    ]


def _print_results(label: str, results: list[dict], n: int) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    for i, r in enumerate(results[:n], 1):
        score_val = next(
            (r[k] for k in ("rrf_score", "score", "distance") if k in r),
            None,
        )
        route = (r.get("metadata") or {}).get("route", r.get("route", ""))
        text_snippet = r.get("text", "")[:120]
        score_str = f"  score={score_val:.6f}" if score_val is not None else ""
        print(f"\n{i}. [{route}]{score_str}")
        print(f"   {text_snippet}...")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search React docs.")
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--mode", choices=["dense", "bm25", "hybrid", "all"], default="hybrid"
    )
    parser.add_argument(
        "--embedder", choices=["local", "openai"], default=None,
        help="must match the active manifest; omitted uses the indexed embedder",
    )
    parser.add_argument("--vector-db", choices=["chroma", "qdrant"], default="qdrant")
    parser.add_argument("--jsonl", default=JSONL_PATH)
    parser.add_argument("--n", type=int, default=5, help="Number of results per mode")
    args = parser.parse_args()

    print(f"Query    : {args.query!r}")
    print(f"Mode     : {args.mode}")
    print(f"Vector DB: {args.vector_db}")

    cache = EmbedCache(EMBED_CACHE_PATH)
    needs_dense = args.mode in ("dense", "hybrid", "all")
    # Qdrant hybrid uses its own internal sparse encoder; manual BM25 only needed for chroma
    needs_bm25 = args.mode in ("bm25", "all") or (
        args.mode == "hybrid" and args.vector_db != "qdrant"
    )

    embedder = store = bm25 = None

    if needs_dense:
        print("\nLoading embedder...")
        manifest_path = Path("output/index_manifest.json")
        if not manifest_path.exists():
            parser.error("output/index_manifest.json is missing; build the index first")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        active_embedder = manifest["embedder"]
        if args.embedder and args.embedder != active_embedder:
            parser.error(
                f"active index uses {active_embedder!r}; rebuild it to change embedders"
            )
        print(f"Embedder : {active_embedder} ({manifest.get('embeddingModel', '')})")
        embedder = build_embedder(active_embedder)
        store = build_vector_store(
            args.vector_db, embedder, collection_name=manifest.get("collectionName")
        )

    if needs_bm25:
        print("Building BM25 index from JSONL...")
        children = _load_children(args.jsonl)
        bm25 = BM25Store()
        bm25.build(children)
        print(f"  Indexed {len(children)} child chunks.")

    if args.mode in ("dense", "all"):
        results = dense_search(args.query, embedder, cache, store, n=args.n)
        _print_results("DENSE (semantic)", results, args.n)

    if args.mode in ("bm25", "all"):
        results = bm25_search(args.query, bm25, n=args.n)
        _print_results("BM25 (keyword)", results, args.n)

    if args.mode in ("hybrid", "all"):
        if args.vector_db == "qdrant":
            query_vec = embed_query(args.query, embedder, cache)
            results = store.query_hybrid(args.query, query_vec, n_results=args.n)
        else:
            results = hybrid_search(args.query, embedder, cache, store, bm25, n=args.n)
        _print_results("HYBRID (RRF)", results, args.n)


if __name__ == "__main__":
    main()
