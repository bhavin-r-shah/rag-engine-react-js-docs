"""CLI entry point: embed child chunks and upsert to a vector store.

Usage:
    python -m react_docs_chunker.indexing.cli [--embedder {local,openai}] [--vector-db {chroma}]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from react_docs_chunker.config import (
    CHROMA_COLLECTION,
    CHROMA_DB_DIR,
    EMBED_CACHE_PATH,
    EMBEDDING_BATCH_SIZE,
    JSONL_PATH,
)
from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.indexing.indexer import run_indexing


def _build_embedder(name: str):
    if name == "local":
        from react_docs_chunker.embed.local_embedder import SentenceTransformerEmbedder
        return SentenceTransformerEmbedder()
    if name == "openai":
        from react_docs_chunker.embed.openai_embedder import OpenAIEmbedder
        return OpenAIEmbedder()
    raise ValueError(f"Unknown embedder: {name}")


def _build_vector_store(name: str, embedder):
    if name == "chroma":
        from react_docs_chunker.indexing.vector_store import ChromaVectorStore
        return ChromaVectorStore(
            model_id=embedder.model_id,
            dimensions=embedder.dimensions,
            db_dir=CHROMA_DB_DIR,
            collection_name=CHROMA_COLLECTION,
        )
    raise ValueError(f"Unknown vector-db: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed React doc chunks and upsert to a vector store.")
    parser.add_argument("--embedder", choices=["local", "openai"], default="local")
    parser.add_argument("--vector-db", choices=["chroma"], default="chroma")
    parser.add_argument("--jsonl", default=JSONL_PATH)
    args = parser.parse_args()

    print(f"Embedder : {args.embedder}")
    print(f"Vector DB: {args.vector_db}")
    print(f"JSONL    : {args.jsonl}")

    if not Path(args.jsonl).exists():
        print("\nJSONL not found — running chunker first...")
        import tiktoken
        from react_docs_chunker.chunker import chunk_corpus
        from react_docs_chunker.config import TOKENIZER_ENCODING
        encoding = tiktoken.get_encoding(TOKENIZER_ENCODING)
        chunk_corpus(
            Path("react-js-docs").resolve(),
            Path(args.jsonl).resolve(),
            lambda text: len(encoding.encode(text)),
        )
        print("Chunking complete.\n")

    embedder = _build_embedder(args.embedder)
    cache = EmbedCache(EMBED_CACHE_PATH)
    store = _build_vector_store(args.vector_db, embedder)

    stats = run_indexing(args.jsonl, embedder, cache, store, batch_size=EMBEDDING_BATCH_SIZE)

    print(f"\nDone.")
    print(f"  Total children : {stats['total_children']}")
    print(f"  Cache hits     : {stats['cache_hits']}")
    print(f"  Newly embedded : {stats['newly_embedded']}")


if __name__ == "__main__":
    main()
