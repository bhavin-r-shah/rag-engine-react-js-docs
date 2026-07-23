# Retrieval design

## Online responsibility

Retrieval runs for every user question against the already-built offline index. Dense
and hybrid search create a fresh query embedding; the document vectors are not rebuilt.

## Search methods

- **Dense** embeds the question and retrieves nearby child vectors from ChromaDB.
- **BM25** ranks exact terms using an in-memory index built from JSONL.
- **Hybrid** retrieves candidates from both methods and combines their positions with
  Reciprocal Rank Fusion (RRF).

`Top K` controls how many final chunks are returned. It is safe to change Top K and
search method per question because neither changes the stored index.

## Result and citation shape

The reusable `RAGService` returns each child ID, matched text, parent text, score,
route, title, heading path, and a citation URL formed from the source URL and anchor.
The browser renders the generated answer separately from the retrieved evidence.

The current system does not apply query filters or a second model reranker. BM25
uses simple lowercase whitespace tokenization, so punctuation-aware lexical analysis
is a future improvement.
