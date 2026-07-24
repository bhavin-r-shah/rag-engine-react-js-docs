"""ChromaDB vector store backend."""

from __future__ import annotations

import chromadb

from react_docs_chunker.config import CHROMA_COLLECTION, CHROMA_DB_DIR
from react_docs_chunker.indexing.vector_store import VectorStore


class ChromaVectorStore(VectorStore):
    """Persistent ChromaDB store. Stores child chunks only; ids = chunkId."""

    def __init__(
        self,
        model_id: str,
        dimensions: int,
        db_dir: str | None = None,
        collection_name: str | None = None,
        client: chromadb.ClientAPI | None = None,
    ) -> None:
        self._client = client or chromadb.PersistentClient(path=db_dir or CHROMA_DB_DIR)
        col_name = collection_name or CHROMA_COLLECTION

        existing = self._client.list_collections()
        existing_names = [c.name for c in existing]

        if col_name in existing_names:
            self._col = self._client.get_collection(col_name)
            stored = self._col.metadata or {}
            stored_model = stored.get("model_id")
            stored_dims = stored.get("dimensions")
            if stored_model and stored_model != model_id:
                raise ValueError(
                    f"Collection '{col_name}' was built with model '{stored_model}' "
                    f"but current model is '{model_id}'. Delete {db_dir or CHROMA_DB_DIR} to reindex."
                )
            if stored_dims and int(stored_dims) != dimensions:
                raise ValueError(
                    f"Collection '{col_name}' has {stored_dims} dimensions "
                    f"but current model produces {dimensions}."
                )
        else:
            self._col = self._client.create_collection(
                name=col_name,
                metadata={"model_id": model_id, "dimensions": dimensions},
            )

    def upsert_chunks(self, records: list[dict], embeddings: list[list[float]]) -> None:
        ids = [r["chunkId"] for r in records]
        if len(ids) != len(set(ids)):
            raise ValueError("Cannot upsert chunks because chunk IDs are not unique")
        documents = [r["text"] for r in records]
        metadatas = [
            {
                "parentId": r.get("parentId", ""),
                "route": r.get("route", ""),
                "docType": r.get("docType", ""),
                "title": r.get("title", ""),
                "anchor": r.get("anchor", ""),
                "contentKind": r.get("contentKind", ""),
                "tokenCount": r.get("tokenCount", 0),
                "sourceUrl": r.get("sourceUrl", ""),
                "sourcePath": r.get("sourcePath", ""),
            }
            for r in records
        ]
        self._col.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def query_dense(
        self, query_embedding: list[float], n_results: int,
        metadata_filters: dict[str, str] | None = None,
    ) -> list[dict]:
        clauses = [{key: {"$eq": value}} for key, value in (metadata_filters or {}).items()]
        where = clauses[0] if len(clauses) == 1 else ({"$and": clauses} if clauses else None)
        kwargs = {"query_embeddings": [query_embedding], "n_results": n_results}
        if where:
            kwargs["where"] = where
        result = self._col.query(**kwargs)
        return [
            {"chunkId": id_, "text": doc, "metadata": meta, "distance": dist}
            for id_, doc, meta, dist in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            )
        ]

    def query_hybrid(
        self, query_text: str, query_embedding: list[float], n_results: int
    ) -> list[dict]:
        raise NotImplementedError(
            "ChromaDB does not support native hybrid search. "
            "Use search/engine.py hybrid_search() instead."
        )

    def close(self) -> None:
        self._client.close()

