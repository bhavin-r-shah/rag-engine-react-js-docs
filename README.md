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
stores them in ChromaDB, and searches them from a command line. You do not need to
know Python or AI to try the local workflow.

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

## Step-by-step: from documents to search results

The easiest beginner path uses the free local embedding model. It does not require an
API key, although it downloads the model the first time it runs.

### 1. Install and activate the project

Install Git and Python 3.12 first. Then open a terminal (Command Prompt on Windows),
clone the repository, and enter it:

```bash
git clone <repository-url>
cd rag-engine-react-js-docs
```

Create an isolated Python environment and install the chunking, local embedding,
ChromaDB, search, and test dependencies.

**Windows Command Prompt:**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e ".[test,embed]"
```

**macOS, Ubuntu, or Debian terminal:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,embed]'
```

On macOS, Homebrew can install Python with `brew install python@3.12 git`. On Ubuntu
or Debian, install it with
`sudo apt install -y git python3.12 python3.12-venv python3-pip` after `sudo apt update`.

### 2. Run ingestion and chunking

Run this command from the repository root while the virtual environment is active:

```bash
python -m react_docs_chunker.cli
```

On Windows Command Prompt, the command is identical. It performs two stages:

1. **Ingestion** discovers `.md` and `.mdx` files in `react-js-docs/`, reads them as
   text, and adds source metadata.
2. **Chunking** separates each document by Markdown headings and divides oversized
   sections into smaller child chunks.

It writes `output/react-doc-chunks.jsonl`. Parent records keep complete sections;
child records are the pieces that the next stage embeds and searches.

### 3. Create embeddings and index them in ChromaDB

```bash
python -m react_docs_chunker.indexing.cli --embedder local --vector-db chroma
```

The command reads only child records, uses the local `all-mpnet-base-v2` model to turn
their text into number lists called **embeddings**, and upserts them into the
`react_docs` collection in `output/chroma_db/`. Similar meanings produce nearby
vectors, which enables semantic search. Embeddings are cached in
`output/embed_cache.db`, so a later indexing run can reuse unchanged work.

If the JSONL file is missing, the indexing command runs ingestion and chunking for
you. Running step 2 explicitly is still recommended while learning because it makes
each pipeline stage visible.

### 4. Search with a user query

Put the question in quotes:

```bash
python -m react_docs_chunker.search.cli "How do I update state based on the previous state?" --mode hybrid --n 5
```

The default `hybrid` mode combines **dense search** (meaning similarity in ChromaDB)
with **BM25 search** (exact-word matching over the JSONL chunks). Reciprocal Rank
Fusion (RRF) combines the two ranked lists. The terminal prints the top five routes,
scores, and text previews. It returns relevant source chunks, **not a generated
chatbot answer**.

Other useful modes are:

```bash
python -m react_docs_chunker.search.cli "useEffect cleanup" --mode dense --n 5
python -m react_docs_chunker.search.cli "useEffect cleanup" --mode bm25 --n 5
python -m react_docs_chunker.search.cli "useEffect cleanup" --mode all --n 5
```

Dense and hybrid search must use the same embedding provider used for indexing.
BM25-only search rebuilds its in-memory keyword index from JSONL and does not need
ChromaDB or an embedding model at query time.

### 5. Optional: use OpenAI embeddings

Install the provider dependencies and set your key before indexing:

```bash
python -m pip install -e '.[embed,embed-openai]'
export OPENAI_API_KEY="your-api-key"
python -m react_docs_chunker.indexing.cli --embedder openai
python -m react_docs_chunker.search.cli "What does useMemo do?" --embedder openai
```

On Windows Command Prompt, set the key with `set OPENAI_API_KEY=your-api-key`. Do not
commit a key. A Chroma collection records its model and vector dimensions; delete
`output/chroma_db/` and re-index before switching between local and OpenAI models.

### 6. Verify the installation

```bash
python -m pytest
```

## Is there a web UI?

**No.** PR #8 implements Python command-line indexing and search, not a browser UI,
React search page, query API, or answer-generating chatbot. Enter the query in the
terminal as shown above and read the ranked chunk previews there. A UI and grounded
AI answer generation remain future work.

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

The project now embeds, indexes, and searches retrieval chunks. It does not expose a
web UI or HTTP API, hydrate complete parent sections in CLI output, rerank with a
model, or call a generative AI model to compose an answer. See
[`low-level-design.md`](low-level-design.md) for the exact implementation boundary.

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
