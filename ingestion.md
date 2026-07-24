# Ingestion design

## Responsibility and status

Ingestion turns the React documentation corpus into deterministic, traceable records
for downstream RAG stages. File discovery, safe text loading, metadata derivation,
chunking invocation, and JSONL serialization are **implemented**. The explicit offline indexing command invokes this stage before embedding and storage. Incremental
manifests, staging, atomic promotion, and production reports are **proposed**.

## Implemented pipeline

1. [`chunk_corpus`](python-src/react_docs_chunker/chunker.py#L257-L280) recursively
   discovers regular, non-symlink `.md` and `.mdx` files case-insensitively and sorts
   them for reproducible traversal.
2. [`chunk_document`](python-src/react_docs_chunker/chunker.py#L218-L254) reads each
   file as UTF-8 text. Source is never rendered or executed.
3. [`_split_frontmatter`](python-src/react_docs_chunker/chunker.py#L73-L87) removes an
   optional opening YAML block and reads only scalar `title` or `meta` values. An
   unmatched marker remains ordinary content to avoid silent data loss.
4. [`_source_metadata`](python-src/react_docs_chunker/chunker.py#L198-L215) derives a
   corpus-relative source path, React route and URL, first-segment document type, and
   SHA-256 checksum of the original text.
5. [`_stable_id`](python-src/react_docs_chunker/chunker.py#L57-L62) hashes identity
   components with separators. Document IDs remain independent of corpus insertion
   order; parent and child positions disambiguate repeated identical content within a
   document while remaining deterministic for an unchanged input.
6. The document is passed into the [chunking stage](chunking.md), after which
   [`chunk_corpus`](python-src/react_docs_chunker/chunker.py#L275-L280) writes one JSON
   object per line to the configured output path.

The CLI defaults to `react-js-docs/` and `output/react-doc-chunks.jsonl`; it builds a
`cl100k_base` token counter and forwards numeric overrides to `chunk_corpus` in
[`cli.py`](python-src/react_docs_chunker/cli.py#L24-L48).

## Record provenance

Every parent and child contains `recordType`, `documentId`, `chunkId`, `sourcePath`,
`sourceUrl`, `route`, `docType`, `sourceHash`, `title`, `headingPath`, `anchor`,
`contentKind`, `chunkIndex`, `tokenCount`, and `text`. Children additionally contain
`parentId`. Record construction is implemented in
[`chunk_document`](python-src/react_docs_chunker/chunker.py#L238-L253).

## Proposed incremental ingestion

Persist a versioned manifest containing source checksums, document and chunk IDs,
schema and pipeline versions, embedding model identity, and the last successful
ingestion time. Compare a new scan with the active manifest:

- **added:** parse, chunk, embed, and upsert;
- **changed:** regenerate the entire document, replace its records, and remove stale
  chunk IDs;
- **unchanged:** reuse records and cached embeddings;
- **deleted:** remove all records associated with the document ID.

Write records into a staging namespace, validate the complete candidate corpus, and
atomically promote it. A failed run must leave the active index and manifest intact.
These capabilities are not present in the current Python package.

## Proposed validation and observability

Before promotion, validate discovered-versus-parsed counts, empty documents or
chunks, duplicate routes and IDs, unsupported MDX, missing titles, malformed URLs or
anchors, token outliers, parent/child integrity, missing embeddings, vector dimensions,
and unexpected loss of fenced examples.

Emit structured logs and a machine-readable report with document state counts,
parent/child counts, token percentiles, warnings, failures, timings, token volume,
index writes, and embedding-cache hit rate. Do not log credentials, vector payloads,
or unnecessary document bodies.
