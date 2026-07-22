# Retrieval design

## Responsibility and status

Retrieval finds the child chunks most relevant to a query. PR #8 implements three
command-line modes: dense, BM25, and hybrid. Model reranking and parent hydration are
not implemented.

## Implemented search methods

- **Dense search** embeds the query with the selected provider and asks ChromaDB for
  the nearest child vectors. It is useful when the query and document express a
  similar idea with different words.
- **BM25 search** lowercases and whitespace-splits every child from JSONL, then ranks
  exact-word matches with `rank-bm25`. Its index exists only for the current search
  process.
- **Hybrid search** fetches three times the requested result count from dense and
  BM25, then combines their ranks with Reciprocal Rank Fusion (RRF). A chunk receives
  credit from either list and more credit when both methods rank it highly.

The implementations are in [`engine.py`](python-src/react_docs_chunker/search/engine.py)
and [`bm25.py`](python-src/react_docs_chunker/search/bm25.py).

## Run retrieval

```bash
python -m react_docs_chunker.search.cli "How does effect cleanup work?" --mode hybrid --n 5
```

Use `--mode dense`, `--mode bm25`, or `--mode all` to compare methods. Dense and hybrid
modes require a previously built Chroma index and the same embedder used to build it.
BM25 mode needs only the JSONL chunks.

The CLI prints rank, route, score, and the first 120 characters of each child. Results
retain source metadata internally, but the current display is not a complete citation
or generated answer. Query filters, model reranking, parent-section hydration,
evaluation thresholds, and degraded-backend handling remain proposed improvements.
