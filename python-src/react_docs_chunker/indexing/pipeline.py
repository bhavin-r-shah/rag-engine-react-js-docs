"""One-time offline ingestion, chunking, embedding, and indexing pipeline."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import tiktoken

from react_docs_chunker._cli_utils import build_embedder, build_vector_store
from react_docs_chunker.chunker import chunk_corpus
from react_docs_chunker.config import (
    EMBED_CACHE_PATH, EMBEDDING_BATCH_SIZE, TOKENIZER_ENCODING,
)
from react_docs_chunker.embed.cache import EmbedCache


def build_index(
    corpus: str | Path,
    jsonl_path: str | Path,
    embedder_name: str = "local",
    chunking_method: str = "markdown",
    target_tokens: int = 600,
    max_tokens: int = 900,
    overlap_tokens: int = 75,
    manifest_path: str | Path = "output/index_manifest.json",
) -> dict:
    """Run every offline stage explicitly; callers decide when this one-time work runs."""
    from react_docs_chunker.indexing.indexer import run_indexing

    encoding = tiktoken.get_encoding(TOKENIZER_ENCODING)
    count = lambda text: len(encoding.encode(text))
    jsonl_path = Path(jsonl_path)
    staging_jsonl = jsonl_path.with_name(f".{jsonl_path.name}.staging")
    collection_name = f"react_docs_{uuid4().hex[:12]}"
    record_count = chunk_corpus(
        Path(corpus).resolve(), staging_jsonl.resolve(), count,
        target_tokens, max_tokens, overlap_tokens, chunking_method,
    )
    embedder = build_embedder(embedder_name)
    cache = EmbedCache(EMBED_CACHE_PATH)
    store = build_vector_store("chroma", embedder, collection_name=collection_name)
    stats = run_indexing(
        staging_jsonl, embedder, cache, store, batch_size=EMBEDDING_BATCH_SIZE
    )
    manifest = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "recordCount": record_count,
        "childCount": stats["total_children"],
        "chunkingMethod": chunking_method,
        "targetTokens": target_tokens,
        "maxTokens": max_tokens,
        "overlapTokens": overlap_tokens,
        "tokenizer": TOKENIZER_ENCODING,
        "embedder": embedder_name,
        "embeddingModel": embedder.model_id,
        "dimensions": embedder.dimensions,
        "collectionName": collection_name,
    }
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_staging = path.with_name(f".{path.name}.staging")
    manifest_staging.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    staging_jsonl.replace(jsonl_path)
    manifest_staging.replace(path)
    return {**manifest, **stats}
