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

All methods require `0 <= overlap < target <= maximum`. Children include stable IDs,
parent IDs, provenance, token counts, and text. Changing the method or token settings
changes the searchable corpus, so run the offline indexing pipeline again. These are
not per-question options.
