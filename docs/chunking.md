# Chunking design

## Responsibility

Chunking turns long Markdown documents into smaller child records for search. Every
strategy also creates parent records that preserve broader document or section text.
The offline indexing pipeline runs chunking before document embeddings are created.

## Available methods

Select a method with `--chunking-method` in either the chunking or indexing command.

### Markdown-aware (`markdown`)

This default method recognizes Markdown headings outside fenced code. Each non-empty
heading section becomes a parent. Small sections produce one searchable child; large
sections are packed from complete paragraphs and code blocks. Each child begins with
its heading breadcrumb. Oversized indivisible blocks fall back to a safe token-budget
split.

This method is recommended for the React corpus because API headings and code examples
carry important meaning.

### Fixed length with overlap (`fixed`)

The complete document becomes a parent. Text is accumulated until the configured
target token budget is reached, then a new child begins with trailing text from the
previous child. `--overlap-tokens` controls the repeated context.

Use this method to compare predictable chunk sizes with semantic chunking:

```bash
python -m react_docs_chunker.cli --chunking-method fixed \
  --target-tokens 400 --max-tokens 400 --overlap-tokens 50
```

### Recursive (`recursive`)

The complete document becomes a parent. The splitter tries progressively smaller
boundaries: blank lines, lines, sentence endings, spaces, and finally fixed pieces.
It then packs neighboring pieces up to the target and can carry a configured overlap.
This preserves natural boundaries better than fixed splitting when Markdown headings
are unreliable.

## Shared rules

All methods require `0 <= overlap < target <= maximum`. Children include deterministic
IDs, parent IDs, provenance, token counts, and text. Section and child positions make
IDs unique even when one document repeats identical headings or text. Changing the
method or token settings changes the searchable corpus, so run the offline indexing
pipeline again. These are not per-question options.

## Default configuration

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

## Running the chunker standalone

The `python -m react_docs_chunker.indexing.cli` pipeline (see
[`db-storage-indexing.md`](db-storage-indexing.md)) runs chunking automatically. To run
chunking alone — for example to inspect JSONL output without embedding or indexing —
use the chunker CLI directly with explicit paths and overrides:

```bash
python -m react_docs_chunker.cli ./react-js-docs ./output/custom.jsonl \
  --target-tokens 600 --max-tokens 900 --overlap-tokens 75 --chunking-method markdown
```

On Windows Command Prompt, put the same command on one line:

```bat
python -m react_docs_chunker.cli .\react-js-docs .\output\custom.jsonl --target-tokens 600 --max-tokens 900 --overlap-tokens 75
```

Run `python -m react_docs_chunker.cli --help` to see every option. See
[`ingestion.md`](ingestion.md) for the JSONL record shape this command produces.
