# Database storage and indexing design

## One-time offline pipeline

Run ingestion, chunking, document embedding, and vector storage before interactive
questions:

```bash
python -m react_docs_chunker.indexing.cli --chunking-method markdown --embedder local --vector-db qdrant
```

Run this command once for a chosen corpus and configuration. Run it again only after
source documents, chunking settings, the embedding model, or the vector database
change.

## Choosing a vector database

`--vector-db` selects the backend. Both `VectorStore` implementations share the same
interface (`upsert_chunks`, `query_dense`, `query_hybrid`, `close`), so either one works
with either embedder and the same metadata filters:

| Backend | CLI value | Storage | Hybrid search |
| --- | --- | --- | --- |
| Qdrant | `qdrant` (default) | `output/qdrant_db/`, embedded locally — no server or Docker | Native: dense + `fastembed` BM25-style sparse vectors fused by Qdrant in one query (RRF). |
| ChromaDB | `chroma` | `output/chroma_db/`, persistent Chroma collection | Manual: `search/engine.py::hybrid_search` fuses ChromaDB dense results with a separately-built in-memory BM25 index using Reciprocal Rank Fusion in Python. |

The active backend is recorded in the manifest (`vectorDb`) so every online query
automatically targets the same store the index was built with — there is no separate
flag to keep in sync at query time.

## Stored outputs

- `output/react-doc-chunks.jsonl` contains parents and searchable children.
- `output/embed_cache.db` caches document embeddings.
- `output/qdrant_db/` or `output/chroma_db/` contains the persistent vector index,
  depending on `--vector-db`.
- `output/index_manifest.json` records creation time, chunk method and sizes,
  tokenizer, embedding provider/model, dimensions, vector database, and record counts.

Each backend stores every child's stable `chunkId`, vector, text, parent ID, route,
document type, title, anchor, content kind, token count, source URL, and source path
(Qdrant additionally stores a sparse BM25 vector per child). Upserts avoid duplicates
when the same ID is indexed again. Stored collection metadata rejects an incompatible
embedding model or vector dimension.

Before any embedding work begins, the indexer verifies that all child IDs are unique.
Each vector-store adapter checks again immediately before upsert, providing a clear
project error instead of a late database duplicate-ID error.

Each build writes to a new collection (named with a fresh UUID suffix) and records
that collection name in the manifest. JSONL and the manifest are replaced only after
indexing succeeds. Therefore a chunking, embedding, or vector-database change cannot
leave stale chunks active, and a failed build does not redirect queries away from the
previous manifest. Older collections are retained for manual cleanup and rollback.

BM25 is not persisted for the ChromaDB path; the online process rebuilds its in-memory
keyword index from JSONL on every run. The local UI exposes a clearly labelled
Build/Rebuild action, but it never starts offline indexing automatically when a user
asks a question.
