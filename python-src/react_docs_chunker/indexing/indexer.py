"""Read JSONL, embed child records, upsert to a vector store."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.embed.embedder import EmbeddingProvider

if TYPE_CHECKING:
    from react_docs_chunker.indexing.vector_store import VectorStore


def run_indexing(
    jsonl_path: str | Path,
    embedder: EmbeddingProvider,
    cache: EmbedCache,
    vector_store: VectorStore,
    batch_size: int = 32,
) -> dict:
    jsonl_path = Path(jsonl_path)
    children = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("recordType") == "child"
    ]

    id_counts = Counter(record["chunkId"] for record in children)
    duplicate_ids = {chunk_id for chunk_id, count in id_counts.items() if count > 1}
    if duplicate_ids:
        examples = []
        for record in children:
            if record["chunkId"] in duplicate_ids:
                examples.append(
                    f"{record['chunkId']} ({record.get('sourcePath', 'unknown source')})"
                )
            if len(examples) == 3:
                break
        raise ValueError(
            f"Found {len(duplicate_ids)} duplicate child chunk ID(s) before embedding. "
            f"Examples: {', '.join(examples)}"
        )

    total = len(children)
    cache_hits = 0
    newly_embedded = 0

    embeddings: list[list[float]] = []

    for start in range(0, total, batch_size):
        batch = children[start : start + batch_size]
        vectors: list[list[float]] = []
        miss_indices: list[int] = []
        miss_texts: list[str] = []

        for i, record in enumerate(batch):
            cached = cache.get(embedder.model_id, record["text"])
            if cached is not None:
                vectors.append(cached)
                cache_hits += 1
            else:
                vectors.append([])  # placeholder
                miss_indices.append(i)
                miss_texts.append(record["text"])

        if miss_texts:
            new_vecs = embedder.embed_batch(miss_texts, batch_size=batch_size)
            newly_embedded += len(new_vecs)
            for idx, vec in zip(miss_indices, new_vecs):
                vectors[idx] = vec
                cache.put(embedder.model_id, batch[idx]["text"], vec)

        embeddings.extend(vectors)

    vector_store.upsert_chunks(children, embeddings)

    return {"total_children": total, "cache_hits": cache_hits, "newly_embedded": newly_embedded}
