"""Local embedded Qdrant vector store with native hybrid search."""

from __future__ import annotations

from react_docs_chunker.config import QDRANT_COLLECTION, QDRANT_DB_DIR
from react_docs_chunker.indexing.vector_store import VectorStore
from qdrant_client import QdrantClient
from qdrant_client import models as qm
from fastembed import SparseTextEmbedding

class QdrantVectorStore(VectorStore):
    """Local embedded Qdrant store with dense + BM25 sparse vectors for native hybrid search."""

    _DENSE_FIELD = "dense"
    _SPARSE_FIELD = "sparse"

    def __init__(
        self,
        model_id: str,
        dimensions: int,
        db_dir: str | None = None,
        collection_name: str | None = None,
        client=None,
        sparse_encoder=None,
    ) -> None:
        self._qm = qm
        self._client = client or QdrantClient(path=db_dir or QDRANT_DB_DIR)
        self._col_name = collection_name or QDRANT_COLLECTION
        self._dimensions = dimensions

        if sparse_encoder is not None:
            self._sparse_enc = sparse_encoder
        else:
            self._sparse_enc = SparseTextEmbedding(model_name="Qdrant/bm25")

        existing = {c.name for c in self._client.get_collections().collections}
        if self._col_name in existing:
            col_info = self._client.get_collection(self._col_name)
            stored_dims = col_info.config.params.vectors[self._DENSE_FIELD].size
            if stored_dims != dimensions:
                raise ValueError(
                    f"Collection '{self._col_name}' has {stored_dims} dimensions "
                    f"but current model produces {dimensions}. "
                    f"Delete {db_dir or QDRANT_DB_DIR} to reindex."
                )
        else:
            self._client.create_collection(
                collection_name=self._col_name,
                vectors_config={
                    self._DENSE_FIELD: qm.VectorParams(
                        size=dimensions,
                        distance=qm.Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    self._SPARSE_FIELD: qm.SparseVectorParams()
                },
            )

    @staticmethod
    def _chunk_id_to_point_id(chunk_id: str) -> int:
        # Stable 63-bit integer from the first 64 bits of the SHA-256 chunkId hex.
        # chunkId is "sha256:<hexdigest>" — strip the prefix before parsing as hex.
        hex_digest = chunk_id.split(":", 1)[-1]
        return int(hex_digest[:16], 16) >> 1

    def upsert_chunks(self, records: list[dict], embeddings: list[list[float]]) -> None:
        texts = [r["text"] for r in records]
        sparse_vecs = list(self._sparse_enc.embed(texts))

        points = []
        for rec, dense_vec, sv in zip(records, embeddings, sparse_vecs):
            payload = {
                "chunkId": rec["chunkId"],
                "parentId": rec.get("parentId", ""),
                "route": rec.get("route", ""),
                "docType": rec.get("docType", ""),
                "title": rec.get("title", ""),
                "anchor": rec.get("anchor", ""),
                "contentKind": rec.get("contentKind", ""),
                "tokenCount": rec.get("tokenCount", 0),
                "sourceUrl": rec.get("sourceUrl", ""),
                "sourcePath": rec.get("sourcePath", ""),
                "text": rec["text"],
            }
            points.append(self._qm.PointStruct(
                id=self._chunk_id_to_point_id(rec["chunkId"]),
                vector={
                    self._DENSE_FIELD: dense_vec,
                    self._SPARSE_FIELD: self._qm.SparseVector(
                        indices=sv.indices.tolist(),
                        values=sv.values.tolist(),
                    ),
                },
                payload=payload,
            ))

        self._client.upsert(collection_name=self._col_name, points=points)

    def query_dense(self, query_embedding: list[float], n_results: int) -> list[dict]:
        hits = self._client.query_points(
            collection_name=self._col_name,
            query=query_embedding,
            using=self._DENSE_FIELD,
            limit=n_results,
        ).points
        return [
            {
                "chunkId": p.payload["chunkId"],
                "text": p.payload.get("text", ""),
                "metadata": {k: v for k, v in p.payload.items() if k not in ("chunkId", "text")},
                "score": p.score,
            }
            for p in hits
        ]

    def query_hybrid(
        self, query_text: str, query_embedding: list[float], n_results: int
    ) -> list[dict]:
        sparse_vecs = list(self._sparse_enc.embed([query_text]))
        sv = sparse_vecs[0]

        hits = self._client.query_points(
            collection_name=self._col_name,
            prefetch=[
                self._qm.Prefetch(
                    query=query_embedding,
                    using=self._DENSE_FIELD,
                    limit=n_results * 3,
                ),
                self._qm.Prefetch(
                    query=self._qm.SparseVector(
                        indices=sv.indices.tolist(),
                        values=sv.values.tolist(),
                    ),
                    using=self._SPARSE_FIELD,
                    limit=n_results * 3,
                ),
            ],
            query=self._qm.FusionQuery(fusion=self._qm.Fusion.RRF),
            limit=n_results,
        ).points
        return [
            {
                "chunkId": p.payload["chunkId"],
                "text": p.payload.get("text", ""),
                "metadata": {k: v for k, v in p.payload.items() if k not in ("chunkId", "text")},
                "rrf_score": p.score,
            }
            for p in hits
        ]
