# React documentation RAG corpus

This repository is a source corpus for building a retrieval-augmented generation
(RAG) application over the official React documentation. The documentation is
mirrored from [`reactjs/react.dev/src/content`](https://github.com/reactjs/react.dev/tree/main/src/content)
into [`docs/`](docs/) while preserving the upstream directory structure.

## Corpus layout

Only Markdown source files (`.md` and `.mdx`, matched case-insensitively) are
included. Keeping the original paths makes it possible to retain useful section
and document metadata when the files are chunked for a vector store.

```text
docs/
├── blog/
├── community/
├── learn/
└── reference/
```

The exact set of directories is controlled by upstream and can change when the
corpus is refreshed.

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

The refresh is atomic: it builds a temporary copy, replaces `docs/` only after
the download succeeds, and writes the resolved upstream commit to
`docs/.react-docs-commit`. Files removed upstream are therefore also removed
locally.

## Using the corpus in a RAG pipeline

A typical ingestion pipeline should:

1. Recursively discover `.md` and `.mdx` files under `docs/`.
2. Parse front matter and headings, retaining the relative file path as source
   metadata.
3. Split text along Markdown section boundaries, with a small overlap between
   chunks.
4. Embed the chunks and upsert them into a vector store.
5. Retrieve relevant chunks for each question and include their source paths in
   the generated answer.

The upstream documentation remains subject to the licensing terms in the React
repository. Review those terms before redistributing or deploying the corpus.
