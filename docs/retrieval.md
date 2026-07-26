# Retrieval design

## Online responsibility

Retrieval runs for every user question against the already-built offline index. Dense
and hybrid search create a fresh query embedding; the document vectors are not rebuilt.

## Search methods

- **Dense** embeds the question and retrieves nearby child vectors from the active
  vector store (ChromaDB or Qdrant — whichever the index manifest names).
- **BM25** ranks exact terms using an in-memory index built from JSONL.
- **Hybrid** retrieves candidates from both methods and fuses their rankings with
  Reciprocal Rank Fusion (RRF). On ChromaDB this fusion happens in Python
  (`search/engine.py::hybrid_search`, combining `query_dense` with the in-memory BM25
  index); on Qdrant it happens natively in a single query (`query_hybrid`, fusing dense
  and Qdrant's own sparse BM25-style vectors). Both paths produce the same
  `rrf_score`-ranked shape. See [`db-storage-indexing.md`](db-storage-indexing.md) for
  how to choose a backend.

`Top K` controls how many final chunks are returned. It is safe to change Top K and
search method per question because neither changes the stored index.

## Metadata filters

The browser can restrict results by exact `docType`, `contentKind`, and `route`.
Selected filters are combined with AND. Dense search passes them to the vector store
before ranking; BM25 builds its in-memory index from matching JSONL children; hybrid
applies the same filters to both candidate lists before RRF. An empty value means
“all.”

The available filter values are derived from child records in the active JSONL index,
so the UI does not ask beginners to guess valid values.

## Result and citation shape

The reusable `RAGService` returns each child ID, matched text, parent text, score,
route, title, heading path, and a citation URL formed from the source URL and anchor.
The browser renders the generated answer separately from the retrieved evidence.

The current system does not apply a second model reranker. BM25 uses simple lowercase
whitespace tokenization, so punctuation-aware lexical analysis is a future improvement.
