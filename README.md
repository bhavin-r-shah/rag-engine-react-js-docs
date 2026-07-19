# React documentation RAG corpus and Python chunker

> [!WARNING]
> **This project is under construction.** It is intended only for personal learning
> and development, is not ready for production, and should not be used as a public
> service or relied on by external users.

This project turns the Markdown files from the official React documentation into
small JSON records called **chunks**. A future AI search or retrieval-augmented
generation (RAG) application can search these chunks and give the relevant text to
an AI model. You do not need to know Python or AI to run the chunking command.

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

## Step-by-step setup and run instructions

Open a terminal in the folder where you want this repository, then follow the section
for your operating system. If you already downloaded the repository, skip the `git
clone` command and use `cd` to enter its folder.

### Windows 10 or 11 (Command Prompt)

1. Install Git and Python by copying these commands into **Command Prompt**:

```bat
winget install --id Git.Git -e --source winget
winget install --id Python.Python.3.12 -e --source winget
```

2. Close Command Prompt, open it again, and verify the installations:

```bat
git --version
python --version
```

3. Download the repository and enter its directory. Replace `<repository-url>` with
   this repository's Git URL:

```bat
git clone <repository-url>
cd rag-engine-react-js-docs
```

4. Create a private Python environment for this project, activate it, and install all
   runtime and test prerequisites:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

5. Run the complete implemented ingestion and chunking workflow:

```bat
python -m react_docs_chunker.cli
```

6. Confirm that the output was created, then run the automated tests:

```bat
dir output\react-doc-chunks.jsonl
python -m pytest
```

When returning to the project later, run these commands from the repository folder:

```bat
.venv\Scripts\activate.bat
python -m react_docs_chunker.cli
```

### macOS (Terminal)

1. Install Apple's command-line tools and Homebrew, then install Python and Git:

```bash
xcode-select --install
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.12 git
```

2. Download, set up, run, and test the project. Replace `<repository-url>` with this
   repository's Git URL:

```bash
git clone <repository-url>
cd rag-engine-react-js-docs
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
python -m react_docs_chunker.cli
ls -lh output/react-doc-chunks.jsonl
python -m pytest
```

### Ubuntu or Debian Linux (Terminal)

1. Install Git, Python, and the Python virtual-environment prerequisite:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
```

2. Download, set up, run, and test the project. Replace `<repository-url>` with this
   repository's Git URL:

```bash
git clone <repository-url>
cd rag-engine-react-js-docs
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
python -m react_docs_chunker.cli
ls -lh output/react-doc-chunks.jsonl
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

The Python command prepares retrieval chunks, but it does not yet create embeddings,
store vectors, search the chunks, or call an AI model. Those later RAG stages are
described in [`low-level-design.md`](low-level-design.md).

The upstream documentation remains subject to the licensing terms in the React
repository. Review those terms before redistributing or deploying the corpus.
