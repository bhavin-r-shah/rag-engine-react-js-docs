"""Shared CLI helpers for building embedders and vector stores."""

from __future__ import annotations

from react_docs_chunker.config import (
    CHROMA_COLLECTION,
    CHROMA_DB_DIR,
    QDRANT_COLLECTION,
    QDRANT_DB_DIR,
)


def build_embedder(name: str):
    if name == "local":
        from react_docs_chunker.embed.local_embedder import SentenceTransformerEmbedder
        return SentenceTransformerEmbedder()
    if name == "openai":
        from react_docs_chunker.embed.openai_embedder import OpenAIEmbedder
        return OpenAIEmbedder()
    raise ValueError(f"Unknown embedder: {name}")


def build_vector_store(name: str, embedder, collection_name: str | None = None):
    if name == "chroma":
        from react_docs_chunker.indexing.chroma_store import ChromaVectorStore
        return ChromaVectorStore(
            model_id=embedder.model_id,
            dimensions=embedder.dimensions,
            db_dir=CHROMA_DB_DIR,
            collection_name=collection_name or CHROMA_COLLECTION,
        )
    if name == "qdrant":
        from react_docs_chunker.indexing.qdrant_store import QdrantVectorStore
        return QdrantVectorStore(
            model_id=embedder.model_id,
            dimensions=embedder.dimensions,
            db_dir=QDRANT_DB_DIR,
            collection_name=collection_name or QDRANT_COLLECTION,
        )
    raise ValueError(f"Unknown vector-db: {name}")
