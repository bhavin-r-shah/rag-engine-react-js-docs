"""CLI for the one-time offline ingestion, chunking, embedding, and indexing run."""
from __future__ import annotations

import argparse

from react_docs_chunker.chunker import CHUNKING_METHODS
from react_docs_chunker.config import JSONL_PATH, MAX_TOKENS, OVERLAP_TOKENS, TARGET_TOKENS
from react_docs_chunker.indexing.pipeline import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the React documentation search index.")
    parser.add_argument("--embedder", choices=["local", "openai"], default="local")
    parser.add_argument("--vector-db", choices=["chroma", "qdrant"], default="qdrant")
    parser.add_argument("--corpus", default="react-js-docs")
    parser.add_argument("--jsonl", default=JSONL_PATH)
    parser.add_argument("--chunking-method", choices=CHUNKING_METHODS, default="markdown")
    parser.add_argument("--target-tokens", type=int, default=TARGET_TOKENS)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--overlap-tokens", type=int, default=OVERLAP_TOKENS)
    args = parser.parse_args()

    print("Running the offline pipeline: ingest -> chunk -> embed -> index")
    result = build_index(
        args.corpus, args.jsonl, args.embedder, args.chunking_method,
        args.target_tokens, args.max_tokens, args.overlap_tokens,
        vector_db_name=args.vector_db,
    )
    print("\nIndex ready. Run this command again only when documents or index settings change.")
    print(f"  Chunking method: {result['chunkingMethod']}")
    print(f"  Total children : {result['total_children']}")
    print(f"  Cache hits     : {result['cache_hits']}")
    print(f"  Newly embedded : {result['newly_embedded']}")


if __name__ == "__main__":
    main()
