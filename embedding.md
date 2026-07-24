# Embedding design

## Offline document embeddings

An embedding is a number vector representing text. During the one-time offline
pipeline, only child records are embedded and stored in ChromaDB. Parent records stay
in JSONL for expanded context and citations.

The supported providers implement `EmbeddingProvider`:

- `local` uses Sentence Transformers and defaults to `all-mpnet-base-v2`;
- `openai` uses `text-embedding-3-small` by default and reads `OPENAI_API_KEY`.

Document embeddings are cached in `output/embed_cache.db` by exact text and model ID.
A repeat offline build can therefore reuse unchanged embeddings.

## Online query embeddings

Every dense or hybrid search embeds the current user query again with the same
provider/model used to build the Chroma collection. Query embeddings are deliberately
not reused from the document cache. BM25-only search does not create a query vector.

Embedding models do not write natural-language answers. After retrieval, the separate
generation adapter can send the question and cited evidence to the configured chat
model.
