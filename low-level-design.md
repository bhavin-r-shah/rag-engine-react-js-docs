# React documentation RAG: low-level design

## Purpose and scope

This repository implements the retrieval portion of a small RAG pipeline for the
Markdown and MDX files in `react-js-docs/`. It preserves headings and provenance,
creates searchable child chunks, embeds them, stores their vectors, and retrieves
relevant text. It does not yet generate an AI answer.

## Implemented end-to-end flow

```text
React Markdown/MDX
        |
        v
ingestion -> heading-aware parent/child chunking -> JSONL
                                                        |
                                                        v
                                      embedding -> ChromaDB index
                                                        |
user terminal query -> dense search + BM25 -> RRF ranking -> chunk previews
```

| Stage | Input | Output | Status |
| --- | --- | --- | --- |
| [Ingestion](ingestion.md) | `react-js-docs/**/*.md(x)` | Safe text and source metadata | **Implemented** |
| [Chunking](chunking.md) | Documents | JSONL parents and children | **Implemented** |
| [Embedding](embedding.md) | Child text | Local or OpenAI vectors and SQLite cache | **Implemented** |
| [Indexing](db-storage-indexing.md) | Children and vectors | Persistent ChromaDB collection | **Implemented** for ChromaDB |
| [Retrieval](retrieval.md) | Query | Dense, BM25, or hybrid ranked children | **Implemented** |
| [User query](user-query.md) | Terminal query | Routes, scores, and text previews | **Implemented** as a CLI only |
| Answer generation | Retrieved evidence | Grounded answer and citations | **Not implemented** |

## Commands and data flow

1. `python -m react_docs_chunker.cli` writes
   `output/react-doc-chunks.jsonl`.
2. `python -m react_docs_chunker.indexing.cli --embedder local` reads children,
   reuses or writes `output/embed_cache.db`, and upserts vectors plus metadata into
   `output/chroma_db/`.
3. `python -m react_docs_chunker.search.cli "query" --mode hybrid` embeds the query,
   searches ChromaDB, builds an in-memory BM25 index from JSONL, fuses the two rankings,
   and prints previews.

Console scripts `chunk-react-docs`, `index-react-docs`, and `search-react-docs` are
installed equivalents. All application code is Python; this repository does not run a
Node.js server or React UI.

## Implemented components

- `chunker.py` handles discovery, metadata, stable IDs, heading-aware sections,
  token-bounded children, and JSONL serialization.
- `embed/` provides a provider interface, Sentence Transformers and OpenAI adapters,
  batching, and a model-and-text-scoped SQLite cache.
- `indexing/` coordinates embedding and idempotent child upserts. Its ChromaDB adapter
  checks collection model identity and vector dimensions.
- `search/` implements query embedding, Chroma dense retrieval, in-memory BM25, and
  reciprocal-rank fusion.

## Important current boundaries

- ChromaDB is the only vector database implementation.
- BM25 is rebuilt from JSONL for every search process rather than persisted.
- ChromaDB stores child text and metadata; parents remain in JSONL and are not hydrated
  into CLI results.
- Search output is evidence, not a synthesized answer or complete citation display.
- There is no web UI, HTTP API, authentication, query filtering, model reranker,
  incremental manifest, stale-record deletion, staging namespace, or atomic index
  promotion.

## Cross-stage rules

- A child is the searchable unit; its `parentId` identifies its complete section.
- Stable `chunkId` values are both cache/index identities and idempotent upsert keys.
- Search must use the same embedding model as its Chroma collection.
- Provenance metadata travels with each indexed child so future interfaces can create
  links and citations.
- Source Markdown, examples, and user queries are data and must never be executed.
