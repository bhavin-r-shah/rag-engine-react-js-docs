# React documentation RAG corpus

This repository is a source corpus for building a retrieval-augmented generation
(RAG) application over the official React documentation. The documentation is
mirrored from [`reactjs/react.dev/src/content`](https://github.com/reactjs/react.dev/tree/main/src/content)
into [`react-js-docs/`](react-js-docs/) as a flat collection.

## Corpus layout

Only Markdown source files (`.md` and `.mdx`, matched case-insensitively) are
included. Every file is placed directly in `react-js-docs/`; upstream path
separators are replaced with `--` so files with the same basename remain unique.

```text
react-js-docs/
├── index.md
├── learn--your-first-component.md
└── reference--react--useState.md
```

The exact set of files is controlled by upstream and can change when the corpus
is refreshed.

## Refresh the documentation

Run the sync script from anywhere in this repository:

```bash
./scripts/sync-react-docs.sh
```

By default, the script downloads the `main` branch. Set `REACT_DOCS_REF` to pin
a tag, branch, or commit for a reproducible corpus:

```bash
REACT_DOCS_REF=v19.1.0 ./scripts/sync-react-docs.sh
```

The refresh is atomic: it builds a temporary copy, replaces `react-js-docs/`
only after the download succeeds, and writes the resolved upstream commit to
`react-js-docs/.react-docs-commit`. Files removed upstream are therefore also
removed locally.

## Run the project with Python

### Prerequisites

- Python 3.10 or newer

The complete implemented ingestion and chunking workflow is Python-only. Node.js
and npm are not required. Create an isolated environment and install the command
from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

Read every Markdown/MDX file in `react-js-docs/` and write retrieval-ready JSON
Lines records by running:

```bash
chunk-react-docs
# Equivalent Python module form:
python -m react_docs_chunker.cli
```

The default output is `output/react-doc-chunks.jsonl`. Override the input, output,
and token settings when experimenting with retrieval quality:

```bash
chunk-react-docs ./react-js-docs ./output/custom.jsonl \
  --target-tokens 600 --max-tokens 900 --overlap-tokens 75
```

Run the Python tests with:

```bash
pytest
```

Each output line is a parent or child record containing stable IDs, source path
and URL, route, document type, source checksum, heading breadcrumbs, anchor,
content kind, token count, and retrieval text. The recommended strategy is
heading-aware parent/child chunking: keep a complete section as the parent,
retrieve smaller 400–700-token children, preserve code with its explanation, and
use 50–100 tokens of overlap only when an oversized section must be divided.
These are starting values; tune them using retrieval recall and citation accuracy
for your application.

## Using the corpus in a RAG pipeline

A complete ingestion pipeline will:

1. Discover `.md` and `.mdx` files directly under `react-js-docs/`.
2. Parse front matter and headings into an AST, retaining the flattened filename
   as source metadata.
3. Split text along Markdown section boundaries, with a small overlap between
   chunks.
4. Embed the chunks and upsert them into a vector store.
5. Retrieve relevant chunks for each question and include their source paths in
   the generated answer.

The upstream documentation remains subject to the licensing terms in the React
repository. Review those terms before redistributing or deploying the corpus.
