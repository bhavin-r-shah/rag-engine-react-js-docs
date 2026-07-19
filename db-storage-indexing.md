# Database storage and indexing design

## Responsibility and status

This stage will persist records and expose complementary semantic and exact-match
indexes. It is **proposed**. The only implemented storage is newline-delimited JSON
written by [`chunk_corpus`](python-src/react_docs_chunker/chunker.py#L257-L280); the
repository does not currently connect to a vector database or search engine.

## Proposed logical records

- **Documents:** document ID, source path/URL, route, type, checksum, and pipeline
  version.
- **Parents:** parent chunk ID, document ID, complete section content, heading path,
  anchor, content kind, and provenance.
- **Children:** child chunk ID, parent ID, retrieval text, token count, metadata, and
  embedding compatibility fields.
- **Manifest:** source-to-record membership, schema and pipeline versions, embedding
  model/dimensions, namespace, and successful ingestion time.

Stable IDs are primary keys. Writes are idempotent upserts; replacing a changed
document also deletes old chunk IDs absent from its new manifest. Deleting a source
removes its children, parents, and document record without affecting unrelated files.

## Proposed indexes

Index child vectors for dense semantic similarity and child text in a lexical/BM25
index for exact API names, props, error numbers, and phrases. Index route, document
type, heading path, anchor, content kind, and publication date where available as
filterable metadata. Parent bodies may be stored outside the high-cardinality search
index but must resolve efficiently by `parentId`.

The [retrieval stage](retrieval.md) queries both child indexes, fuses their candidates,
and hydrates parent content only after ranking.

## Atomic publication

Build each run in a new staging namespace:

1. Upsert all staged documents, parents, children, vectors, and lexical fields.
2. Verify counts, unique IDs, parent references, vector presence/dimensions, metadata,
   and manifest membership.
3. Mark the manifest complete only after all validation succeeds.
4. Atomically switch the active alias or namespace pointer to the staged index.
5. Retain or garbage-collect the previous namespace according to rollback policy.

No failed or partially written namespace may become active. Readers continue using the
previously validated namespace throughout staging.
