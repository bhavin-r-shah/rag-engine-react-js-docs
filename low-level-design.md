# React documentation RAG: low-level design

## Purpose and scope

This design describes an end-to-end retrieval-augmented generation (RAG) system for
the Markdown and MDX files in `react-js-docs/`. The pipeline must preserve titles,
heading hierarchy, React API identifiers, prose, examples, and provenance instead of
splitting source files at arbitrary character boundaries.

Only deterministic document ingestion and structure-aware parent/child chunking are
implemented today. Embedding, database indexing, retrieval, and answer generation are
designs for subsequent milestones; their documents label proposed behavior explicitly.

## End-to-end flow

```text
React Markdown/MDX
        |
        v
ingestion -> chunking -> embedding -> database storage and indexing
                                                   |
                                                   v
user query -> retrieval --------------------> grounded answer + citations
```

| Stage | Responsibility | Input | Output | Status |
| --- | --- | --- | --- | --- |
| [Ingestion](ingestion.md) | Discover files, read safe text, derive provenance, and serialize records. | `react-js-docs/**/*.md(x)` | Deterministic document metadata and JSONL records | **Implemented** for discovery, metadata, and JSONL; incremental ingestion is proposed. |
| [Chunking](chunking.md) | Split each document first by heading section and then oversized sections by block/token limits. | Document body, title, metadata | Section parents and retrieval children | **Implemented** in Python. |
| [Embedding](embedding.md) | Convert retrieval children into model-compatible dense vectors. | Child retrieval text | Versioned vectors and embedding metadata | **Proposed**. |
| [Database storage and indexing](db-storage-indexing.md) | Store parents/children and build vector plus lexical indexes atomically. | Records, vectors, manifest | Searchable active index | **Proposed**; JSONL output is the only current storage. |
| [Retrieval](retrieval.md) | Find, fuse, optionally rerank, and hydrate relevant evidence. | Validated search query | Ranked children, parents, and citations | **Proposed**. |
| [User query](user-query.md) | Orchestrate query handling, context construction, grounded generation, and response telemetry. | User question | Answer with source citations | **Proposed**. |

## Implemented Python architecture

```text
react-js-docs/**/*.md(x)
        |
        v
safe, deterministic discovery and metadata derivation
        |
        v
front-matter, fence, block, and heading scanner
        |
        v
heading sections (parents)
        |
        v
token-bounded retrieval chunks (children)
        |
        v
output/react-doc-chunks.jsonl
```

The installed `chunk-react-docs` command and `python -m react_docs_chunker.cli` are
equivalent. Both use `python-src/react_docs_chunker/`; there is no Node.js ingestion
runtime.

## Implementation boundary

The Python package currently implements discovery, safe text loading, limited
front-matter parsing, metadata and stable-ID derivation, heading-aware chunking,
model-token counting, and JSONL serialization. It does **not** generate embeddings,
write a vector or lexical database, maintain an incremental manifest, retrieve or
rerank evidence, or answer user questions.

This boundary is intentional: later integrations remain behind the contracts in the
linked stage designs, allowing providers and storage engines to change without
rewriting the structure-aware ingestion core.

## Cross-stage contracts

- A child is the searchable unit; its `parentId` resolves to the complete semantic
  section used for display or expanded context.
- Stable document and chunk IDs are the upsert, cache, and deletion keys.
- Every searchable record retains source path, URL, route, checksum, title, heading
  path, anchor, content kind, token count, and text for filtering and citations.
- Embedding model identity and vector dimensions are part of index compatibility.
- Only a completely validated staged index may replace the active index.
- Retrieval returns evidence and provenance; query orchestration is responsible for
  passing that evidence to a generator and rendering citations.

## Operational and security principles

- Treat the corpus and user input as untrusted; never execute source content.
- Keep transformations deterministic, idempotent, and independently testable.
- Fail explicitly on ambiguous identity or corrupt provenance; warn on recoverable
  syntax.
- Keep model, embedding, and database integrations behind interfaces.
- Version schemas, pipeline behavior, manifests, models, indexes, and evaluations.
- Never log credentials, vectors, unnecessary complete documents, or sensitive query
  content.
- Preserve the previously serving corpus until a replacement passes every quality
  gate.
