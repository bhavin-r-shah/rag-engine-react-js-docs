"""Shared test doubles and factories for the embed/indexing/search test suite.

Import from here instead of redefining a stub embedder or a fake child record —
`test_indexer.py`, `test_search.py`, and `test_vector_store.py` all need the same
handful of building blocks. This module only imports light, always-installed
dependencies at module scope (no chromadb/qdrant/numpy), so it is safe to import from
dependency-free tests too (e.g. `test_indexer_validation.py`).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from react_docs_chunker.embed.embedder import EmbeddingProvider


class StubEmbedder(EmbeddingProvider):
    """Deterministic, content-based fake embedder: same text -> same vector, always.

    No model download or network call, so tests run offline. Because vectors are
    derived from the text itself rather than its position in a batch, a query
    re-embedded later still lands on the same vector as when that text was indexed.
    """

    DIMS = 4

    def __init__(self, model: str = "stub-model") -> None:
        self._model = model
        self.call_count = 0

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self.DIMS

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        self.call_count += 1
        result = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            result.append([float(digest[i]) / 255.0 for i in range(self.DIMS)])
        return result


class StubSparseEncoder:
    """Deterministic sparse (BM25-style) encoder; no fastembed model download."""

    def embed(self, texts):
        import numpy as np

        for text in texts:
            words = list(dict.fromkeys(text.lower().split()))
            indices = np.array([abs(hash(w)) % 10_000 for w in words], dtype=np.int32)
            values = np.ones(len(words), dtype=np.float32) / max(len(words), 1)
            yield SimpleNamespace(indices=indices, values=values)


def make_child(chunk_id: str, text: str, **overrides) -> dict:
    """Build a minimal child JSONL record; pass field overrides as keyword args."""
    record = {
        "recordType": "child",
        "chunkId": chunk_id,
        "parentId": "p1",
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
    record.update(overrides)
    return record


def write_jsonl(tmp_path: Path, records: list[dict], filename: str = "chunks.jsonl") -> str:
    """Write records as JSON Lines under tmp_path and return the path as a string."""
    path = Path(tmp_path) / filename
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return str(path)


def chroma_store(embedder, collection_name: str | None = None):
    """An in-memory ChromaVectorStore with a fresh, isolated collection per call.

    A random collection name is used by default: chromadb's EphemeralClient shares
    its underlying system across instances with matching settings, so two tests that
    both used the default collection name could otherwise see each other's records.
    """
    import chromadb

    from react_docs_chunker.indexing.chroma_store import ChromaVectorStore

    return ChromaVectorStore(
        model_id=embedder.model_id,
        dimensions=embedder.dimensions,
        client=chromadb.EphemeralClient(),
        collection_name=collection_name or f"test_{uuid4().hex[:12]}",
    )


def qdrant_store(embedder, collection_name: str | None = None):
    """An in-memory QdrantVectorStore with a stub sparse encoder (no model download)."""
    from qdrant_client import QdrantClient

    from react_docs_chunker.indexing.qdrant_store import QdrantVectorStore

    return QdrantVectorStore(
        model_id=embedder.model_id,
        dimensions=embedder.dimensions,
        client=QdrantClient(":memory:"),
        collection_name=collection_name or f"test_{uuid4().hex[:12]}",
        sparse_encoder=StubSparseEncoder(),
    )
