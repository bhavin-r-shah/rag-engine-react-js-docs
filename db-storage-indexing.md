# Database storage and indexing design

## One-time offline pipeline

Run ingestion, chunking, document embedding, and vector storage before interactive
questions:

```bash
python -m react_docs_chunker.indexing.cli --chunking-method markdown --embedder local
```

Run this command once for a chosen corpus and configuration. Run it again only after
source documents, chunking settings, or the embedding model change.

## Stored outputs

- `output/react-doc-chunks.jsonl` contains parents and searchable children.
- `output/embed_cache.db` caches document embeddings.
- `output/chroma_db/` contains the persistent `react_docs` Chroma collection.
- `output/index_manifest.json` records creation time, chunk method and sizes,
  tokenizer, embedding provider/model, dimensions, and record counts.

Chroma stores each child's stable `chunkId`, vector, text, parent ID, route, document
type, title, anchor, content kind, token count, source URL, and source path. Upserts
avoid duplicates when the same ID is indexed again. Collection metadata rejects an
incompatible embedding model or vector dimension.

Each build writes to a new Chroma collection and records that collection name in the
manifest. JSONL and the manifest are replaced only after indexing succeeds. Therefore
a chunking or embedding change cannot leave stale chunks in the active collection,
and a failed build does not redirect queries away from the previous manifest. Older
collections are retained for manual cleanup and rollback.

BM25 is not persisted; the online process rebuilds its in-memory keyword index from
JSONL. ChromaDB is currently the only vector database. The local UI exposes a clearly
labelled Build/Rebuild action, but it never starts offline indexing automatically when
a user asks a question.
