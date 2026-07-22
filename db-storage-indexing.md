# Database storage and indexing design

## Responsibility and status

Indexing makes child chunks searchable by saving their embeddings and metadata in a
vector database. PR #8 implements persistent **ChromaDB** storage. The JSONL file
remains the source for parent records and for the BM25 keyword index.

## Run indexing

```bash
python -m react_docs_chunker.indexing.cli --embedder local --vector-db chroma
```

If `output/react-doc-chunks.jsonl` does not exist, this command runs the chunker first.
It then embeds child records and upserts them by stable `chunkId`. An **upsert** means
“insert a new ID, or update the existing ID,” so rerunning the command does not create
a second copy of the same chunk.

## What ChromaDB stores

[`ChromaVectorStore`](python-src/react_docs_chunker/indexing/vector_store.py) persists
the `react_docs` collection under `output/chroma_db/`. Each entry contains:

- the child `chunkId`;
- its embedding and searchable text; and
- metadata such as parent ID, route, document type, title, anchor, content kind, token
  count, source URL, and source path.

The collection also records the embedding model ID and dimensions. Opening it with an
incompatible model or vector size raises an error instead of producing misleading
search results. Delete `output/chroma_db/` and index again when intentionally changing
models.

## Current boundaries

Only ChromaDB is selectable. Dense vectors are persistent, but BM25 is rebuilt in
memory from JSONL whenever keyword or hybrid search starts. Parent records are not
written to ChromaDB, and the CLI currently displays child previews rather than loading
the complete parent section. Staging namespaces, atomic promotion, deletion of stale
IDs, and production manifests are not implemented.
