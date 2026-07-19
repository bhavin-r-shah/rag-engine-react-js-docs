# React documentation RAG ingestion: low-level design

## Purpose and scope

This design defines a deterministic, incremental, structure-aware ingestion pipeline for the Markdown and MDX files in `react-js-docs/`. The corpus contains learning guides, API references, warnings, errors, community pages, and dated blog posts. Retrieval units must preserve React documentation semantics—titles, API identifiers, heading hierarchy, prose, and associated examples—instead of splitting raw files at arbitrary character boundaries.

The first implementation milestone covers discovery, syntax-tree parsing, and normalization. Chunking, indexing, incremental updates, validation, and retrieval evaluation are specified here as subsequent milestones.

## End-to-end architecture

```text
react-js-docs/**/*.md(x)
        |
        v
secure deterministic discovery
        |
        v
Markdown/MDX AST parsing
        |
        v
semantic normalization
        |
        v
document -> heading sections -> child chunks
        |              |
        |              +-> lexical/BM25 index
        +-> parent store
                       +-> embedding cache -> vector index
                                              |
                                              v
                                      corpus validation
                                              |
                                              v
                                   atomic index promotion
```

## 1. Discover and classify documents

Recursively discover `.md` and `.mdx` files in stable lexical order. Ignore symbolic links and reject resolved paths outside the configured corpus root. A source record contains its corpus-relative path, inferred document type, route, canonical React URL, SHA-256 source checksum, and raw Markdown.

Flattened names are converted to routes by replacing `--` boundaries with `/` and removing a terminal `index`. For example, `reference--react--useEffect.md` maps to `/reference/react/useEffect` and `https://react.dev/reference/react/useEffect`. The first route segment classifies the document as `learn`, `reference`, `warnings`, `errors`, `blog`, `community`, or another future upstream category. Duplicate routes are fatal.

## 2. Parse Markdown as a syntax tree

Use an AST-capable Markdown/MDX parser, not regular expressions. The parser must understand YAML front matter, explicit heading anchors, fenced code metadata, JSX/MDX wrappers, links, lists, tables, callouts, and inline code. It must retain the tree and parsed front matter as an intermediate representation.

React-specific components are handled deliberately. Semantic wrapper content such as `<Intro>` and Sandpack examples is retained, while presentation-only elements such as `<InlineToc />` are discarded. Unsupported constructs generate warnings rather than silently losing content. Embedded JavaScript, JSX, HTML, and examples are data and are never evaluated.

## 3. Normalize without destroying meaning

Generate two representations:

1. `retrievalText` for embeddings and lexical search. It includes the title, route, prose, exact API identifiers, and useful code.
2. `displayMarkdown` for model context and citations. It preserves readable Markdown, fenced code, and code-fence attributes.

Remove front matter, navigation-only elements, MDX imports/exports, presentation wrappers, explicit heading-comment markup, and redundant whitespace. Do not lowercase, stem, execute, or reformat identifiers such as `useEffect`, `httpEquiv`, and `renderToPipeableStream`. Resolve the title in this order: front-matter `title`, front-matter `meta`, first level-one heading, then final route segment. Hash normalized retrieval content for caching and change detection.

## Current ingest script: behavior, output, and rationale

### Command and execution flow

The current `npm run ingest` command executes `node src/cli.js`. By default, it reads from `react-js-docs/` and writes to `output/normalized-documents.json`. Both locations can be overridden with positional arguments:

```bash
npm run ingest

# Equivalent explicit invocation
node src/cli.js react-js-docs output/normalized-documents.json

# Custom input and output locations
npm run ingest -- ./path/to/corpus ./path/to/output.json
```

The command performs the first three stages of this design in order:

1. **Discover:** recursively find supported documents, validate paths, assign routes and canonical URLs, classify document types, and calculate source checksums.
2. **Parse:** convert each Markdown or MDX document into an abstract syntax tree and parse its YAML front matter.
3. **Normalize:** remove retrieval-irrelevant presentation syntax and produce separate retrieval and display representations.

The destination directory is created automatically. On success, the CLI reports the number of normalized documents, output path, and accumulated warning count. On failure, it prints the error and exits with a nonzero status.

### Discovery record

For each `.md` or `.mdx` source, discovery:

- walks the corpus in deterministic lexical order;
- ignores symbolic links and verifies that resolved paths remain inside the corpus root;
- converts flattened filenames into React routes;
- classifies the document from the first route segment;
- produces a canonical `https://react.dev` URL;
- computes a SHA-256 checksum over the original source; and
- rejects duplicate canonical routes.

For example, `react-js-docs/reference--react--useEffect.md` first becomes approximately:

```json
{
  "sourcePath": "reference--react--useEffect.md",
  "route": "/reference/react/useEffect",
  "docType": "reference",
  "sourceUrl": "https://react.dev/reference/react/useEffect",
  "sourceHash": "<sha256>",
  "rawMarkdown": "<original file contents>"
}
```

A terminal `index` segment is removed: `learn--index.md` becomes `/learn`, while the root `index.md` becomes `/`.

### Parsing behavior

The parser recognizes YAML front matter, headings, paragraphs, inline code, fenced code and its metadata, links, images, lists, MDX flow and text elements, and raw HTML. This structural representation lets later stages distinguish content boundaries rather than treating the document as an arbitrary string.

Invalid YAML is recorded as a recoverable document warning. Raw HTML is preserved as data and also produces a warning. JavaScript, JSX, HTML, MDX expressions, and documentation examples are never executed during ingestion.

### Normalized representations

Normalization produces two representations because retrieval and answer presentation have different requirements.

`retrievalText` is intended for later section-aware chunking, embedding, and lexical indexing. It contains the resolved title, canonical route, searchable prose, exact React identifiers, and useful example content. The title is selected in this order:

1. front-matter `title`;
2. front-matter `meta`;
3. the first level-one heading;
4. the final route segment; or
5. `React` for the root document.

`displayMarkdown` is intended for answer-generation context and citations. It preserves readable Markdown and fenced code while removing YAML front matter, MDX imports and exports, empty wrappers, and presentation-only elements such as `<InlineToc />`. Content nested inside semantic wrappers such as `<Intro>` remains available even though the wrapper itself is removed.

### Output format

The CLI writes a single JSON object with an ingestion timestamp and a `documents` array:

```json
{
  "generatedAt": "2026-07-19T12:34:56.789Z",
  "documents": [
    {
      "sourcePath": "reference--react--useEffect.md",
      "sourceUrl": "https://react.dev/reference/react/useEffect",
      "route": "/reference/react/useEffect",
      "docType": "reference",
      "sourceHash": "f04a...",
      "title": "useEffect",
      "frontmatter": {
        "title": "useEffect"
      },
      "warnings": [],
      "retrievalText": "Title: useEffect\n\nRoute: /reference/react/useEffect\n\n...",
      "displayMarkdown": "# useEffect\n\n`useEffect` is a React Hook...",
      "contentHash": "90bc..."
    }
  ]
}
```

The normalized fields serve the following purposes:

| Field | Purpose |
| --- | --- |
| `sourcePath` | Corpus-relative source provenance |
| `sourceUrl` | Canonical React documentation URL |
| `route` | React documentation route |
| `docType` | Classification such as `learn`, `reference`, or `blog` |
| `sourceHash` | SHA-256 checksum of the original source |
| `title` | Resolved document title |
| `frontmatter` | Parsed YAML metadata |
| `warnings` | Recoverable parsing or content warnings |
| `retrievalText` | Search-oriented normalized content |
| `displayMarkdown` | Human-readable context for generation and citations |
| `contentHash` | SHA-256 checksum of normalized retrieval content |

This file is an intermediate ingestion artifact, not a vector database or completed RAG index.

### Current implementation boundary

The Node normalization command does **not** yet perform the following steps. The
separate Python `chunk-react-docs` command now implements section-aware parent/child
chunking, heading breadcrumbs, token counting, and deterministic chunk IDs:

- generate embeddings;
- build a lexical/BM25 index;
- write to a vector database;
- retrieve or rerank content;
- answer questions; or
- maintain an incremental ingestion manifest.

The remaining responsibilities belong to the subsequent stages specified below.

### Why normalize before chunking raw Markdown

The ingestion stages do not replace chunking. They ensure that chunking operates on clean, understood, traceable document content instead of arbitrary raw Markdown strings.

#### Preserve semantic boundaries

A fixed token or character splitter can divide content in the middle of a fenced JavaScript example, prop list, MDX wrapper, warning, link, or heading and its explanatory paragraph. Parsing first exposes headings, paragraphs, lists, tables, wrappers, and complete code blocks. The chunker can therefore use structural boundaries and keep associated prose and examples together.

#### Remove presentation noise

React documentation contains elements meant for the website renderer rather than retrieval, including YAML front matter, `<InlineToc />`, semantic wrappers, Sandpack components, and MDX imports or exports. Embedding raw Markdown would allow those implementation details to compete with the actual documentation. Normalization removes presentation-only syntax while retaining meaningful child content.

#### Optimize retrieval and presentation independently

A single raw representation is not ideal for both search and answer generation. `retrievalText` explicitly includes search signals such as title and route. `displayMarkdown` retains readable formatting and code for model context and citations. Without this separation, the pipeline must either embed noisy display syntax or strip structure that the answering model needs.

#### Preserve exact API terminology

Identifiers such as `useEffect`, `useEffectEvent`, `useLayoutEffect`, `httpEquiv`, `renderToPipeableStream`, and `exhaustive-deps` must not be lowercased, stemmed, or reformatted. Preserving them supports exact-term retrieval today and a future hybrid semantic-plus-lexical index.

#### Establish provenance before content is divided

Every future chunk can inherit a source file, canonical route and URL, document category, title, original-source checksum, and normalized-content checksum. This supports citations, filters, debugging, change detection, stale-record deletion, and selective re-embedding.

#### Enable deterministic incremental processing

`sourceHash` identifies whether the source file changed. `contentHash` identifies whether its normalized retrieval representation changed. A future manifest can use these identities to reuse unchanged parsing and embedding results and to distinguish formatting-only changes from retrieval-relevant changes.

#### Make quality problems observable

Parsing warnings are attached to individual documents before chunks and embeddings are created. Unsupported syntax, invalid front matter, or risky raw constructs can be inspected and validated rather than being silently embedded.

### Concrete comparison

Given this source:

````mdx
---
meta: "useWidget"
---

<Intro>

Use the `useWidget` Hook to synchronize a widget.

</Intro>

<InlineToc />

## Usage {/*usage*/}

```js src/App.js active
useWidget();
```
````

A direct raw chunk contains YAML syntax, wrapper names, a presentation component, and an anchor comment in addition to the useful documentation. The normalized retrieval representation is closer to:

```text
Title: useWidget

Route: /reference/react/useWidget

Use the useWidget Hook to synchronize a widget.
Usage
useWidget();
```

The display representation remains readable and code-aware:

````md
Use the `useWidget` Hook to synchronize a widget.

## Usage

```js src/App.js active
useWidget();
```
````

The resulting boundary is:

```text
Raw React Markdown
        |
        v
Discover and classify
        |
        v
Parse Markdown/MDX structure
        |
        v
Normalize for retrieval and display
        |
        v
Structured JSON artifact
        |
        v
Section-aware chunking
        |
        v
Embedding and lexical indexing
```

## 4. Section-aware parent-child chunking

Split a source document at headings and attach its full breadcrumb, for example `<meta> > Reference > Props`. Keep small sections intact. Split oversized sections only at paragraph, list, table, or example boundaries, and keep code with its explanatory prose. Do not isolate individual prop-list entries. Apply overlap only to children created from the same oversized section.

This stage is implemented by the Python `chunk-react-docs` command. It reads the
Markdown corpus without evaluating MDX, writes JSON Lines parent and child records,
and uses `cl100k_base` tokenization so limits reflect model tokens rather than raw
characters. A word-level fallback split is used only when a single indivisible block
would otherwise exceed the hard limit.

Initial configurable targets are 400–700 tokens per child, a hard maximum of 800–1,000 tokens, and 50–100 tokens of overlap when a split is necessary. Store the full section as a parent and use smaller children for retrieval. Final values must be selected from retrieval evaluation, not intuition.

## 5. Versioned provenance metadata

Every parent and child record includes `schemaVersion`, `pipelineVersion`, stable `documentId` and `chunkId`, `sourcePath`, `sourceUrl`, `route`, `docType`, `title`, `headingPath`, anchor, content kind, language, optional publication date, source and content hashes, chunk index, and token count. URLs include explicit anchors where available.

IDs derive from stable source identity, section anchor, and normalized content rather than insertion order. Reject missing provenance, malformed URLs, absolute local paths, duplicate IDs, and invalid token counts.

An illustrative chunk record is:

```json
{
  "schemaVersion": 1,
  "documentId": "sha256:...",
  "chunkId": "sha256:...",
  "sourcePath": "react-js-docs/reference--react-dom--components--meta.md",
  "sourceUrl": "https://react.dev/reference/react-dom/components/meta#props",
  "docType": "reference",
  "title": "<meta>",
  "headingPath": ["Reference", "<meta>", "Props"],
  "anchor": "props",
  "contentKind": "prose_and_code",
  "language": "en",
  "publishedAt": null,
  "sourceHash": "sha256:...",
  "chunkIndex": 3,
  "tokenCount": 612
}
```

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
