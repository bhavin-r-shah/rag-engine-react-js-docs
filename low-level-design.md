# React documentation RAG ingestion: low-level design

## Purpose and scope

This design defines a deterministic, incremental, structure-aware ingestion pipeline for the Markdown and MDX files in `react-js-docs/`. The corpus contains learning guides, API references, warnings, errors, community pages, and dated blog posts. Retrieval units must preserve React documentation semantics—titles, API identifiers, heading hierarchy, prose, and associated examples—instead of splitting raw files at arbitrary character boundaries.

The Python implementation covers deterministic discovery, safe Markdown structure parsing, metadata derivation, and section-aware parent/child chunking. Indexing, incremental updates, validation, and retrieval evaluation remain subsequent milestones.

## Implemented Python architecture

```text
react-js-docs/**/*.md(x)
        |
        v
safe, deterministic Python discovery
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

The installed `chunk-react-docs` console command and
`python -m react_docs_chunker.cli` module command are equivalent. Both call the Python
package in `python-src/react_docs_chunker/`; there is no Node.js ingestion runtime.

## 1. Discover and classify documents

`chunk_corpus` recursively discovers `.md` and `.mdx` files case-insensitively, ignores
symbolic links, and sorts paths before processing. Stable ordering makes repeated runs
with identical input deterministic.

Flattened names become React routes by replacing `--` boundaries with `/` and removing
a final `index`. For example, `reference--react--useEffect.md` maps to
`/reference/react/useEffect` and `https://react.dev/reference/react/useEffect`. The
first route segment supplies `docType`. Every record also receives a corpus-relative
source path and SHA-256 checksum of its original UTF-8 text.

## 2. Safely identify Markdown structure

The implementation is a deliberately small, non-executing structure scanner. It reads
documentation as UTF-8 text, extracts scalar `title` or `meta` front-matter values,
recognizes ATX headings and React anchor comments, and groups paragraphs and fenced
code into blocks. Fence state prevents a Python or shell comment beginning with `#`
inside a code example from becoming a heading.

The scanner never imports, evaluates, or renders JavaScript, JSX, MDX, HTML, or fenced
examples. Website-specific MDX wrappers remain inert source text. A future normalization
milestone may use a full Markdown/MDX AST when presentation wrappers must be removed;
the current chunker does not claim full CommonMark or MDX parsing.

## 3. Create section parents and retrieval children

A heading begins a semantic section and its nested heading breadcrumb is attached to
each child. The complete section becomes a parent. Small sections yield one child;
oversized sections are packed at blank-line-separated block boundaries. Complete
fenced examples remain blocks. Overlap copies only complete trailing blocks from the
same section. A word-boundary safety split is used only when one indivisible block
would exceed the hard maximum.

The heading breadcrumb is included in the child's token count. The implementation
reserves those tokens before packing content so a child respects `MAX_TOKENS`. It uses
tiktoken's `cl100k_base` encoding rather than character or word counts.

All default strategy variables live in
`python-src/react_docs_chunker/config.py`: `CHUNK_BY_HEADING`, `TARGET_TOKENS`,
`MAX_TOKENS`, `OVERLAP_TOKENS`, and `TOKENIZER_ENCODING`. CLI flags can temporarily
override the three numeric values.

## 4. Output records

The command writes newline-delimited JSON to `output/react-doc-chunks.jsonl` by default.
Every parent and child includes `recordType`, stable `documentId` and `chunkId`,
`sourcePath`, `sourceUrl`, `route`, `docType`, `sourceHash`, `title`, `headingPath`,
`anchor`, `contentKind`, `chunkIndex`, `tokenCount`, and `text`. A child additionally
contains `parentId`.

IDs derive from source identity, section anchor, and content instead of corpus insertion
order. The program creates the destination directory automatically. The JSONL output is
ready for a later embedding and indexing stage; it is not a vector database.

## 5. Current implementation boundary

The Python command implements discovery, metadata derivation, structure-aware
parent/child chunking, model-token counting, and JSONL serialization. It does not yet
generate embeddings, build a lexical/BM25 index, write to a vector database, retrieve
or rerank content, answer questions, or maintain an incremental ingestion manifest.

## Why structure-aware chunking is recommended

Fixed character windows can split a heading from its explanation or cut through a
fenced example. Heading-first parent/child chunking preserves the subject of a React
API section, while block boundaries keep most prose, lists, and examples coherent.
Source metadata is added before splitting so every retrieved child remains traceable.
Exact identifiers such as `useEffect`, `httpEquiv`, and `renderToPipeableStream` are
preserved for later semantic and lexical retrieval.

## 6. Embedding and hybrid indexing

Use dense vectors for semantic similarity and a lexical/BM25 index for exact identifiers, props, error numbers, and phrases. Store parent content by parent ID and index metadata for filtering by route, type, heading, and publication date. Combine dense and lexical candidates before optional reranking.

The embedding client is provider-agnostic, batched, retryable, rate-limited, and cached by embedding-model identifier plus normalized-content hash. Record model and dimensions with the index and never mix incompatible vectors. All writes are idempotent upserts keyed by stable chunk ID.

## 7. Incremental and atomic ingestion

Persist a manifest of source checksums, document IDs, chunk IDs, schema and pipeline versions, embedding model, and successful ingestion time. Compare the current corpus with the last successful manifest and classify sources as added, changed, unchanged, or deleted. Reuse unchanged records and cached embeddings, fully replace changed-document chunks, and delete records for removed documents.

Write into a staging namespace. Validate the complete staged corpus and atomically promote it; a failed run leaves the previously active index and manifest untouched.

## 8. Quality gates and observability

Before promotion, validate discovered versus parsed counts, empty documents and chunks, duplicate routes and IDs, unsupported MDX, missing titles, malformed anchors and URLs, token-size outliers, orphaned records, missing embeddings, vector dimensions, and unexpected loss of code examples. Every searchable record must contain retrieval text, display content, a compatible embedding, stable provenance, and a resolvable source URL.

Emit structured logs and a JSON report containing document state counts, parent and child counts, token percentiles, warning and failure counts, timings, token volume, index writes, and embedding-cache hit rate. Never log credentials, full embedding payloads, or unnecessary complete documents.

## 9. Retrieval evaluation

Maintain a version-controlled golden dataset covering conceptual learning questions, exact API lookup, code examples, warnings and errors, React Server Components, version-sensitive blog facts, and similar identifiers that require disambiguation. Record acceptable routes, section anchors, and expected facts.

Evaluate dense-only, lexical-only, and hybrid retrieval with recall at K, mean reciprocal rank, and section-level citation accuracy. Use results to choose chunk limits, hybrid fusion weights, metadata boosts, candidate counts, and reranking rather than tuning them manually.

## Operational and security principles

- Treat the corpus as untrusted input and never execute source content.
- Keep transformations deterministic, idempotent, and independently testable.
- Fail explicitly on ambiguous identity or corrupt provenance; warn on recoverable syntax.
- Keep provider and storage integrations behind interfaces.
- Version schemas, pipeline behavior, manifests, indexes, and evaluation data.
- Preserve the previously serving corpus until a replacement passes all quality gates.
