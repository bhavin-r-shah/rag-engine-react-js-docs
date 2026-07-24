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
small JSON records called **chunks**, converts the searchable chunks into embeddings,
stores them in ChromaDB, and searches them from a terminal or local browser UI. You
do not need to know Python or AI to try the workflow.

The input documents are in [`react-js-docs/`](react-js-docs/). The Python program
reads them as text; it never runs JavaScript, JSX, MDX, or code examples found in
the documentation.

## What the program produces

The command creates `output/react-doc-chunks.jsonl`. JSON Lines means that each line
is one complete JSON record. The file contains:

- **parent records**, which preserve complete documentation sections; and
- **child records**, which are smaller pieces intended for AI search.

Every record includes the source file and React URL, title and heading path, stable
IDs, a SHA-256 source checksum, content type, token count, and text. A **token** is a
small unit of text used by an AI model; it is not exactly the same as a word.

## Understand the two parts

The pipeline deliberately separates expensive preparation from interactive questions:

1. **Offline—run once:** ingest documents, chunk them, embed every child, and store the
   vectors in ChromaDB. Run it again only when documents, chunking settings, or the
   embedding model change.
2. **Online—run for every question:** embed the new user query, search the existing
   index, retrieve cited chunks, and optionally ask a chat model for a grounded answer.

## Step-by-step setup and run instructions

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

The indexing command performs ingestion, chunking, document embedding, and ChromaDB
storage in one explicit run:

```bash
python -m react_docs_chunker.indexing.cli \
  --chunking-method markdown \
  --target-tokens 600 \
  --max-tokens 900 \
  --overlap-tokens 75 \
  --embedder local
```

Windows Command Prompt users can put the command on one line. The run creates:

- `output/react-doc-chunks.jsonl` — parent and child records;
- `output/embed_cache.db` — reusable document embeddings;
- `output/chroma_db/` — the persistent vector index; and
- `output/index_manifest.json` — the active chunk and embedding settings.

Do **not** run this command before every question. Rebuild only when the source files
or offline settings change.

### 3. Choose a chunking method

The offline command supports:

| Method | CLI value | When to use it |
| --- | --- | --- |
| Markdown-aware | `markdown` | Recommended for these docs. Keeps headings, breadcrumbs, paragraphs, and fenced code together where possible. |
| Fixed length with overlap | `fixed` | Creates chunks near `--target-tokens` and repeats up to `--overlap-tokens` from the previous chunk. |
| Recursive | `recursive` | Tries paragraphs, lines, sentences, and words in order until each piece fits the token budget. |

For example, create 400-token fixed chunks with 50 tokens of overlap:

```bash
python -m react_docs_chunker.indexing.cli --chunking-method fixed --target-tokens 400 --max-tokens 400 --overlap-tokens 50
```

### 4. Start the browser UI

```bash
python -m react_docs_chunker.ui.app
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The sidebar separates:

- **online controls:** Top K, dense/BM25/hybrid search, and metadata filters; and
- **one-time offline controls:** chunking method, token length, maximum, overlap, and
  document embedder, followed by the explicit Build/Rebuild button.

The active query embedder is read-only because it must match the model used to build
the index. To change it, choose a different document embedder in the offline section
and rebuild the index.

### 5. Use query controls and filters

The UI offers these online controls, which do not rebuild the index:

| Control | Meaning |
| --- | --- |
| `Top K` | Maximum number of retrieved chunks to return, from 1 to 50. |
| `Hybrid` | Combines semantic dense search and exact-word BM25 ranking. |
| `Dense` | Uses a fresh query embedding to find semantically similar chunks. |
| `BM25` | Uses keyword matching and does not embed the query. |
| `Document type` | Limits results to one corpus category, such as `learn`, `reference`, or `blog`. |
| `Content` | Limits results to `prose`, `code`, or `prose_and_code`. |
| `Exact route` | Limits results to one React documentation route. |
| `Generate an LLM answer` | Calls the chat model when selected; otherwise only retrieved evidence is shown. |

The three metadata filters are optional and combined with **AND**. For example,
choosing document type `reference` and content `prose_and_code` returns only chunks
that satisfy both conditions. Filter choices come from the active JSONL index.

Enter a question and select **Ask**. For every question the server embeds that query
again and searches the existing index. The page displays the generated answer plus
expandable retrieved chunks, scores, and clickable React documentation citations.
Clear **Generate an LLM answer** to inspect retrieval without calling the chat model.

The default document/query embedder is local `all-mpnet-base-v2`. The default answer
model is `gpt-4o-mini`, configurable with `OPENAI_CHAT_MODEL`. The same embedding
provider must be used for offline indexing and online dense or hybrid search.

### 6. Optional terminal-only search

The browser is not required for retrieval:

```bash
python -m react_docs_chunker.search.cli "How does effect cleanup work?" --mode hybrid --n 5
```

The terminal command prints retrieved previews but does not generate the final chat
answer.

### 7. Run tests

```bash
python -m pytest
```

## Running with different input, output, or chunk sizes

The default command reads `react-js-docs/` and writes
`output/react-doc-chunks.jsonl`. This example uses explicit paths and temporary size
overrides:

```bash
python -m react_docs_chunker.cli ./react-js-docs ./output/custom.jsonl \
  --target-tokens 600 --max-tokens 900 --overlap-tokens 75
```

On Windows Command Prompt, put the same command on one line:

```bat
python -m react_docs_chunker.cli .\react-js-docs .\output\custom.jsonl --target-tokens 600 --max-tokens 900 --overlap-tokens 75
```

Run `python -m react_docs_chunker.cli --help` to see every option.

## Where the chunking strategy is configured

The default variables are all in
[`python-src/react_docs_chunker/config.py`](python-src/react_docs_chunker/config.py):

| Variable | Default | Meaning |
| --- | ---: | --- |
| `CHUNK_BY_HEADING` | `True` | Start semantic sections at Markdown headings. |
| `TARGET_TOKENS` | `600` | Split an oversized section when a child grows beyond this target. |
| `MAX_TOKENS` | `900` | Hard maximum for a retrieval child, including its heading breadcrumb. |
| `OVERLAP_TOKENS` | `75` | Context repeated between children from the same oversized section. |
| `TOKENIZER_ENCODING` | `cl100k_base` | Token-counting vocabulary used by the program. |

Heading-aware parent/child chunking is recommended because a heading gives React API
text its meaning. The program keeps a complete section as its parent, retrieves
smaller children, keeps fenced code with nearby explanations where possible, and
repeats only complete Markdown blocks for overlap. The defaults are starting values;
measure retrieval recall and citation quality before changing them for production.

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
deployment hardening. See [`low-level-design.md`](low-level-design.md).

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
