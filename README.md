# React documentation RAG corpus and Python chunker

> [!WARNING]
> **This project is under construction.** It is intended only for personal learning
> and development, is not ready for production, and should not be used as a public
> service or relied on by external users.

> [!IMPORTANT]
> **No permission is granted to use or distribute this project.** The repository
> owner's original code and material are all rights reserved and are provided only for
> the owner's personal learning and development. See [`LICENSE`](LICENSE). Third-party
> React documentation remains governed by its own license; see
> [`LICENSE-REACT-DOCS.md`](LICENSE-REACT-DOCS.md).

This project turns the Markdown files from the official React documentation into
small JSON records called **chunks**, converts them into embeddings, stores them in a
local vector database (ChromaDB or Qdrant, your choice), and searches them from a
terminal or local browser UI — with an optional grounded, cited answer from an OpenAI
chat model. You do not need to know Python or AI to try the workflow.

The input documents are in [`react-js-docs/`](react-js-docs/). The Python program
reads them as text; it never runs JavaScript, JSX, MDX, or code examples found in
the documentation.

The pipeline deliberately separates expensive preparation from interactive questions:

1. **Offline — run once:** ingest documents, chunk them, embed every child, and store
   the vectors in the chosen vector database. Run it again only when documents,
   chunking settings, the embedding model, or the vector database change.
2. **Online — run for every question:** embed the new user query, search the existing
   index, retrieve cited chunks, and optionally ask a chat model for a grounded answer.

## Documentation map

This README covers setup and the day-to-day commands. Each pipeline stage has its own
design doc with the full option reference and rationale:

| Doc | Covers |
| --- | --- |
| [`docs/ingestion.md`](docs/ingestion.md) | File discovery, parsing, IDs, and the JSONL record shape. |
| [`docs/chunking.md`](docs/chunking.md) | The three chunking methods, `config.py` defaults, standalone chunker usage. |
| [`docs/embedding.md`](docs/embedding.md) | Local vs. OpenAI embedding providers and the embedding cache. |
| [`docs/db-storage-indexing.md`](docs/db-storage-indexing.md) | ChromaDB vs. Qdrant, stored outputs, the index manifest. |
| [`docs/retrieval.md`](docs/retrieval.md) | Dense, BM25, and hybrid search; metadata filters; citations. |
| [`docs/user-query.md`](docs/user-query.md) | The browser UI's online controls and per-question flow. |
| [`docs/low-level-design.md`](docs/low-level-design.md) | End-to-end architecture and current constraints. |

## Quick start

### 1. Create the Python environment

Install Git and Python 3.12, clone this repository, and enter it:

```bash
git clone <repository-url>
cd rag-engine-react-js-docs
```

**Windows Command Prompt:**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e ".[test,embed,embed-openai]"
```

**macOS or Linux:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,embed,embed-openai]'
```

The OpenAI dependency is needed for generated answers. Set the key only in your
terminal; never commit it:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_CHAT_MODEL="gpt-4o-mini"  # optional override
```

On Windows Command Prompt use `set OPENAI_API_KEY=your-api-key`.

### 2. Run the offline pipeline once

The indexing command performs ingestion, chunking, document embedding, and vector
storage in one explicit run:

```bash
python -m react_docs_chunker.indexing.cli \
  --chunking-method markdown \
  --target-tokens 600 \
  --max-tokens 900 \
  --overlap-tokens 75 \
  --embedder local \
  --vector-db qdrant
```

Windows Command Prompt users can put the command on one line. Do **not** run this
command before every question — rebuild only when the source files or offline
settings change. For the full chunking-method and vector-database comparison, plus
what each run writes to `output/`, see [`docs/chunking.md`](docs/chunking.md) and
[`docs/db-storage-indexing.md`](docs/db-storage-indexing.md).

### 3. Start the browser UI

```bash
python -m react_docs_chunker.ui.app
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The sidebar separates one-time
offline setup (embedder, vector database, chunking method, token settings, plus the
explicit Build/Rebuild button) from online query controls (search mode, Top K,
metadata filters) that run fresh for every question. See
[`docs/user-query.md`](docs/user-query.md) for what each control does and
[`docs/retrieval.md`](docs/retrieval.md) for how search and filtering work.

The default document/query embedder is local `all-mpnet-base-v2`. The default answer
model is `gpt-4o-mini`, configurable with `OPENAI_CHAT_MODEL`.

### 4. Optional: terminal-only search

The browser is not required for retrieval:

```bash
python -m react_docs_chunker.search.cli "How does effect cleanup work?" --mode hybrid --vector-db qdrant --n 5
```

`--vector-db` must match the backend the index was built with. Use `--mode all` to
print dense, BM25, and hybrid results side by side for comparison. This command prints
retrieved previews but does not generate the final chat answer.

### 5. Run tests

```bash
python -m pytest
```

## Refreshing the React documentation corpus

The repository includes the corpus already. To replace it with the newest upstream
React Markdown files, run this optional command from the repository root:

```bash
./scripts/sync-react-docs.sh
```

To refresh from a particular React tag, branch, or commit:

```bash
REACT_DOCS_REF=v19.1.0 ./scripts/sync-react-docs.sh
```

The refresh replaces `react-js-docs/` only after a successful download and records
the upstream commit in `react-js-docs/.react-docs-commit`.

## What this project does not do yet

The project provides a local browser UI and grounded OpenAI answer generation. It is
still a learning application, not a production service: it has no authentication,
concurrent index-build coordination across processes, model reranker, or production
deployment hardening. See [`docs/low-level-design.md`](docs/low-level-design.md#current-constraints).

## React documentation license and attribution

The files in [`react-js-docs/`](react-js-docs/) contain material copied from the
official [React documentation](https://react.dev/) and its
[`reactjs/react.dev`](https://github.com/reactjs/react.dev) source repository.

The React documentation is:

- **Copyright © Meta Platforms, Inc. and affiliates.**
- Licensed under the
  [Creative Commons Attribution 4.0 International license (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
- Governed by React's upstream
  [`LICENSE-DOCS.md`](https://github.com/reactjs/react.dev/blob/main/LICENSE-DOCS.md).
- Documented locally in
  [`LICENSE-REACT-DOCS.md`](LICENSE-REACT-DOCS.md) so the attribution remains available
  with this repository.

This repository redistributes the documentation as flattened Markdown filenames and
may transform that material into parent and child JSONL chunks for retrieval. These
are changes from the upstream presentation. The original documentation and its
license notices remain available at the links above.

CC BY 4.0 allows sharing and adaptation when its terms are followed, including giving
appropriate credit, linking to the license, and indicating whether changes were made.
The attribution above must be retained with copies or adaptations of the React
documentation. It does not imply that Meta or the React team endorses this project.

This attribution applies to the React documentation content. It does not, by itself,
set the license for the original Python code or other original material in this
repository. The repository owner's original material is all rights reserved under the
repository-level [`LICENSE`](LICENSE); no permission is granted for anyone else to
use, copy, modify, distribute, deploy, or host it.

The repository-level restriction cannot remove rights that Meta or another third
party grants directly for its own material. In particular, the React documentation
continues to be available under CC BY 4.0 when that license's conditions are followed.
If the goal is to prevent all third-party access to the project as a whole, keep the
repository private and do not publish generated chunks or copies of the corpus.
