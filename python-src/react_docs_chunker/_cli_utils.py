"""Shared CLI helpers for building embedders and vector stores."""

from __future__ import annotations

from react_docs_chunker.config import CHROMA_COLLECTION, CHROMA_DB_DIR


def build_embedder(name: str):
    if name == "local":
        from react_docs_chunker.embed.local_embedder import SentenceTransformerEmbedder
        return SentenceTransformerEmbedder()
    if name == "openai":
        from react_docs_chunker.embed.openai_embedder import OpenAIEmbedder
        return OpenAIEmbedder()
    raise ValueError(f"Unknown embedder: {name}")


def build_vector_store(name: str, embedder):
    if name == "chroma":
        from react_docs_chunker.indexing.vector_store import ChromaVectorStore
        return ChromaVectorStore(
            model_id=embedder.model_id,
            dimensions=embedder.dimensions,
            db_dir=CHROMA_DB_DIR,
            collection_name=CHROMA_COLLECTION,
        )
    raise ValueError(f"Unknown vector-db: {name}")
