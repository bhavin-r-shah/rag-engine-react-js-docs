# Embedding design

## Responsibility and status

The embedding stage will convert retrieval-child text into dense vectors for semantic
search. It is **proposed**: this repository currently produces JSONL records but has
no embedding client or model integration.

## Proposed contract

An embedding provider adapter accepts a batch of `{chunkId, text}` items plus an
explicit model identifier and returns `{chunkId, vector, model, dimensions}`. The
adapter must:

- batch requests within provider item and token limits;
- apply bounded retries with exponential backoff and jitter to transient failures;
- honor provider rate limits without reordering identity mappings;
- reject missing vectors, non-finite values, and unexpected dimensions;
- expose request counts, token volume, latency, retries, and failures without logging
  raw vectors or unnecessary text.

Providers remain behind this interface so indexing does not depend on a particular
SDK. Authentication comes from runtime secret configuration and is never persisted in
records or logs.

## Cache and compatibility

Cache embeddings by the embedding-model identifier plus a normalized-content hash.
Normalization must be deterministic and versioned; changing it invalidates the cache.
Store model identifier and vector dimensions with every staged index and never mix
incompatible vectors in one vector field.

Only child retrieval text is embedded by default. Parent content remains addressable
through `parentId` for expanded context. Stable `chunkId` values are the idempotent
upsert keys shared with [database storage and indexing](db-storage-indexing.md).

## Failure behavior

A partial embedding batch must not be promoted. Failed items may be retried, but the
staged corpus passes validation only when every searchable child has exactly one
compatible vector. Permanent provider or validation failures leave the active index
unchanged.
