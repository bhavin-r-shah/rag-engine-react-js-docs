# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

This is a Python-only RAG (retrieval-augmented generation) pipeline over the official React
documentation. It covers the full path from raw Markdown to a grounded, cited answer:

1. **Chunking** — Markdown files → structured JSON parent/child chunks (`chunker.py`).
2. **Embedding** — child chunks → vectors, via a swappable local or OpenAI provider (`embed/`).
3. **Indexing** — vectors → a local vector store, ChromaDB or Qdrant (`indexing/`).
4. **Search** — dense, BM25, or hybrid (RRF) retrieval over the index (`search/`).
5. **Generation** — retrieved evidence → a cited answer via an OpenAI chat model (`generation/`).
6. **RAG service + UI** — ties 2–5 together for online queries, with a small local browser UI
   (`rag/`, `ui/`).

Stages 1–3 are offline, one-time (or re-run-on-change) work; stages 4–5 run fresh for every
query.

### Design docs (read on demand, not preloaded)

This file covers what's needed to navigate and edit the code. For design rationale, defaults
tables, and the full CLI/UI option reference, open the relevant doc instead of searching the
code cold:

| Doc | Read it when the task touches... |
| --- | --- |
| `docs/ingestion.md` | file discovery, parsing, ID derivation, the JSONL record shape |
| `docs/chunking.md` | the three chunking methods, `config.py` defaults, chunk-size tuning |
| `docs/embedding.md` | embedding providers, the embedding cache, local vs. OpenAI tradeoffs |
| `docs/db-storage-indexing.md` | vector-store internals, ChromaDB vs. Qdrant, the manifest fields |
| `docs/retrieval.md` | dense/BM25/hybrid search mechanics, metadata filters, citations |
| `docs/user-query.md` | the browser UI's online controls, per-question request flow |
| `docs/low-level-design.md` | end-to-end architecture (Mermaid diagram), current constraints |

## Commands

Activate the virtual environment first on Windows:
```bat
.venv\Scripts\activate.bat
```

On macOS/Linux:
```bash
source .venv/bin/activate
```

Install (including test dependencies):
```bash
python -m pip install -e ".[test]"
```

Install with local embedding + both vector-store backends (sentence-transformers, chromadb,
rank-bm25, qdrant-client, fastembed):
```bash
python -m pip install -e ".[embed,test]"
```

Install with the OpenAI embedder instead of / alongside local:
```bash
python -m pip install -e ".[embed-openai,test]"
export OPENAI_API_KEY=sk-...   # also required for answer generation
```

Run the chunker only (default paths):
```bash
python -m react_docs_chunker.cli
```

Run with custom paths, chunk size overrides, and chunking method:
```bash
python -m react_docs_chunker.cli ./react-js-docs ./output/custom.jsonl --target-tokens 600 --max-tokens 900 --overlap-tokens 75 --chunking-method markdown
```

Run the full offline pipeline — chunk, embed, and index in one step (auto-runs the chunker if
the JSONL is missing):
```bash
python -m react_docs_chunker.indexing.cli --embedder local --vector-db qdrant
```

Search the index directly from the CLI (dense, BM25, hybrid, or all three side by side):
```bash
python -m react_docs_chunker.search.cli "how does useEffect cleanup work" --mode all --vector-db qdrant
```

Run the local browser UI (build/rebuild the index and ask questions):
```bash
python -m react_docs_chunker.ui.app
```

Run all tests:
```bash
python -m pytest
```

Run a single test:
```bash
python -m pytest tests/test_chunker.py::test_chunks_nested_headings_and_preserves_code
```

Refresh the React docs corpus from upstream:
```bash
./scripts/sync-react-docs.sh
```

## Architecture

`react-js-docs/*.md` → `chunker.py` → `output/react-doc-chunks.jsonl` → `indexing/pipeline.py`
(`build_index`, using `embed/` + `indexing/`) → `output/index_manifest.json` →
`search/engine.py` + `rag/service.py` (online: dense/BM25/hybrid search + citations) →
`generation/openai_generator.py` (optional). Full offline/online Mermaid diagram:
`docs/low-level-design.md`.

Package layout under `python-src/react_docs_chunker/`:

- **`config.py`** — all default strategy constants: chunking (`TARGET_TOKENS`, `MAX_TOKENS`,
  `OVERLAP_TOKENS`, `CHUNK_BY_HEADING`, `TOKENIZER_ENCODING`), embedding (`EMBEDDING_BATCH_SIZE`,
  `DEFAULT_LOCAL_MODEL`, `DEFAULT_OPENAI_MODEL`), and output paths (`JSONL_PATH`,
  `EMBED_CACHE_PATH`, `CHROMA_DB_DIR`/`CHROMA_COLLECTION`, `QDRANT_DB_DIR`/`QDRANT_COLLECTION`).
  This is the first file to edit when experimenting with chunk sizes or defaults.
- **`chunker.py`** — discovers `.md`/`.mdx` files, strips front matter, groups text under
  headings into `Section` dataclasses, packs blocks into token-bounded child chunks (via one of
  `CHUNKING_METHODS = ("markdown", "fixed", "recursive")`), and serializes parent+child records
  as JSONL.
- **`cli.py`** — thin argparse wrapper around `chunk_corpus`; registered as `chunk-react-docs`.
- **`_cli_utils.py`** — shared `build_embedder(name)` / `build_vector_store(name, embedder, ...)`
  factories used by every CLI and by `rag/service.py`, so backend selection logic lives in one
  place.
- **`embed/`** — `embedder.py` defines the `EmbeddingProvider` ABC (`model_id`, `dimensions`,
  `embed_batch`); `local_embedder.py` (`SentenceTransformerEmbedder`, fully offline) and
  `openai_embedder.py` (`OpenAIEmbedder`, retried with exponential backoff) implement it;
  `cache.py` is a SQLite cache keyed by `sha256(model_id + "\0" + text)` so re-runs only embed
  new/changed text.
- **`indexing/`** — `vector_store.py` defines the `VectorStore` ABC (`upsert_chunks`,
  `query_dense` with optional `metadata_filters`, `query_hybrid`, `close`); `chroma_store.py`
  (`ChromaVectorStore`) and `qdrant_store.py` (`QdrantVectorStore`) implement it — see
  `docs/db-storage-indexing.md` for how the two backends differ. `indexer.py::run_indexing()` reads
  the JSONL, checks the embedding cache, embeds cache misses in batches, and upserts idempotently
  (duplicate `chunkId`s are rejected before embedding). `pipeline.py::build_index()` runs
  ingest → chunk → embed → index end-to-end and writes `output/index_manifest.json`. `cli.py` is
  the `index-react-docs` entry point (`--embedder {local,openai}`, `--vector-db {chroma,qdrant}`).
- **`search/`** — `bm25.py` (`BM25Store`) builds an in-memory keyword index from child records at
  startup (rebuilt from JSONL in seconds, no persistence). `engine.py` provides `dense_search`,
  `bm25_search`, and `hybrid_search`; see `docs/retrieval.md` for how hybrid fusion differs between
  Chroma (manual RRF here) and Qdrant (native, via `QdrantVectorStore.query_hybrid`). `cli.py` is
  the `search-react-docs` entry point (`--mode {dense,bm25,hybrid,all}`).
- **`generation/`** — `provider.py` defines the `GenerationProvider` ABC (`model_id`, `generate`);
  `openai_generator.py` (`OpenAIGenerator`) answers strictly from supplied evidence, citing
  `[S1]`-style labels, and requires `OPENAI_API_KEY`.
- **`rag/service.py`** — `RAGService.query()` is the single reusable entry point used by both the
  CLI-adjacent tooling and the browser UI: validates input, reads the manifest to pick the
  matching embedder/vector-db, applies exact-match metadata filters (`docType`, `contentKind`,
  `route`) before ranking, runs the chosen search mode, builds citations, and optionally
  generates an answer.
- **`ui/`** — `app.py` is a dependency-free `http.server`-based local UI (`rag-react-docs-ui`
  entry point) serving `index.html` and two JSON endpoints: `POST /api/index` (runs
  `build_index`) and `POST /api/query` (runs `RAGService.query`). `index.html` is a single
  self-contained page with offline setup controls (embedder, vector-db, chunking method, token
  settings) and an online query panel (search mode, top K, metadata filters).

### Key design constraints

- The scanner **never executes** source content (no JS, JSX, MDX, or HTML rendering). Treat
  corpus files as untrusted text.
- IDs (`documentId`, `chunkId`) are SHA-256 hashes (`"sha256:" + hexdigest`) derived from source
  identity and content, not insertion order — repeated runs with identical input are
  deterministic and idempotent. Any code deriving a numeric ID from `chunkId` (e.g. Qdrant point
  IDs) must strip the `"sha256:"` prefix before parsing as hex.
- Token counting uses `tiktoken` (`cl100k_base`) rather than characters or words, matching the
  token budget of OpenAI-family embedding models. Note this is *not* the tokenizer the local
  `all-mpnet-base-v2` model uses internally (384-token max sequence length) — chunk-size settings
  tuned for OpenAI embeddings can silently truncate under the local embedder.
  Heading breadcrumbs are included in each child's token count before packing, so children
  always respect `MAX_TOKENS`.
- File names in `react-js-docs/` use `--` as a path separator (e.g.
  `reference--react--useEffect.md` → `/reference/react/useEffect`).
- Both `EmbeddingProvider` and `VectorStore` are swappable via ABCs, resolved only through
  `_cli_utils.build_embedder` / `build_vector_store` — don't hardcode a backend name in new call
  sites; read it from the index manifest (`vectorDb`, `embedder`) like `rag/service.py` does.
- `VectorStore` implementations (and `EmbedCache`) own real connections and must be `close()`d;
  callers open them and close them in a `finally` block (see `pipeline.py`, `search/cli.py`,
  `rag/service.py` for the pattern).
- `ChromaVectorStore.query_hybrid` intentionally raises `NotImplementedError` — Chroma hybrid
  search is done by `search/engine.py::hybrid_search` (manual RRF over `query_dense` + BM25).
  `QdrantVectorStore.query_hybrid` does native RRF fusion in a single Qdrant call.

### Output record shape

Every JSONL record contains: `recordType`, `documentId`, `chunkId`, `sourcePath`, `sourceUrl`,
`route`, `docType`, `sourceHash`, `title`, `headingPath`, `anchor`, `contentKind`, `chunkIndex`,
`tokenCount`, `text`. Child records additionally include `parentId`. Full field-by-field
rationale: `docs/ingestion.md`.

### Index manifest (`output/index_manifest.json`)

Written by `build_index()` after a successful offline run; online query code reads it to select
the matching embedder and vector-store backend instead of re-guessing. Full field list and the
Chroma/Qdrant comparison: `docs/db-storage-indexing.md`.

## Tests

Tests live flat in `tests/`, one file per stage, and follow the existing pattern of building
tiny fixtures/stubs rather than mocking internals:

- **`_test_utils.py`** — shared, not a test file itself: `StubEmbedder` (deterministic,
  content-based SHA-256 vectors), `StubSparseEncoder`, `make_child()` (child-record factory),
  `write_jsonl()`, `chroma_store()`, `qdrant_store()`. Only stdlib + `EmbeddingProvider` are
  imported at module scope, so importing it doesn't pull in chromadb/qdrant/numpy — safe for
  dependency-free tests too. Prefer these over redefining a local stub/factory.
- **`test_chunker.py`** — builds tiny temporary corpora with `tmp_path`, calls `chunk_corpus`
  directly with a simple word-count function instead of tiktoken.
- **`test_embedder.py`** — uses `StubEmbedder` from `_test_utils` to exercise `EmbedCache`
  hit/miss behavior with no model download.
- **`test_indexer.py`** / **`test_vector_store.py`** — use `chroma_store()` / `qdrant_store()`
  from `_test_utils` (in-memory, no disk), so no network calls or model downloads happen in CI.
- **`test_indexer_validation.py`** — dependency-free checks (duplicate-ID rejection, etc.) using
  a plain `TrackingEmbedder`/fake store, runnable without ChromaDB or Qdrant installed.
- **`test_search.py`** — dense/BM25/hybrid ranking assertions against an in-memory Chroma store.
- **`test_rag_service.py`** — dependency-free validation of `RAGService` input checks and the
  metadata-filter logic (`_filter_children`), without touching real embedders or stores.

When adding tests, follow this pattern: reuse `_test_utils` where it fits, and otherwise build a
minimal in-memory/temp-path fixture and a stub implementation of the relevant ABC, rather than
mocking chunker/indexer/search internals.
