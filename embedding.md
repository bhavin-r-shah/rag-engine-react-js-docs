# Embedding design

## Responsibility and status

An **embedding** is a list of numbers that represents a piece of text. Texts with
similar meanings should have nearby embeddings. PR #8 implements this stage for child
chunks; parent sections are not embedded.

## Implemented providers

Both providers follow the `EmbeddingProvider` interface in
[`embedder.py`](python-src/react_docs_chunker/embed/embedder.py):

- `local` uses Sentence Transformers and defaults to `all-mpnet-base-v2` (768
  dimensions). It needs no API key, but downloads the model on first use.
- `openai` uses the OpenAI embeddings API and defaults to
  `text-embedding-3-small`. It reads `OPENAI_API_KEY`, batches requests, and retries a
  failed API call up to five times with exponential waiting.

The index and search commands must use the same provider and model because vectors
from different models are not comparable.

## How embedding runs

Run embedding as part of indexing:

```bash
python -m react_docs_chunker.indexing.cli --embedder local
```

[`run_indexing`](python-src/react_docs_chunker/indexing/indexer.py) reads JSONL child
records in batches. For each child it checks the cache, embeds cache misses, saves new
vectors, and sends all records and vectors to the vector store.

## Cache

[`EmbedCache`](python-src/react_docs_chunker/embed/cache.py) stores vectors in the
SQLite file `output/embed_cache.db`. Its key is a SHA-256 hash of both model ID and
exact text. Therefore:

- the same model and text can reuse an old vector;
- changed text creates a new cache entry; and
- different models cannot accidentally share an entry.

The CLI reports cache hits and newly embedded children after indexing. The current
implementation does not validate non-finite vector values or atomically publish a
fully staged embedding run; those remain future hardening work.
