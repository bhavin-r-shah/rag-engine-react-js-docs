import json

import pytest

from react_docs_chunker.chunker import chunk_corpus


def word_count(text: str) -> int:
    """A dependency-free test counter; production uses the tiktoken tokenizer."""
    return len(text.split())


def test_chunks_nested_headings_and_preserves_code(tmp_path):
    corpus = tmp_path / "react-js-docs"
    corpus.mkdir()
    (corpus / "guide.md").write_text("""---
title: Beginner Guide
---
## Setup {/*setup*/}

Explain the example.

```js
const answer = 42;
```

### Details

More details here.
""", encoding="utf-8")
    output = tmp_path / "chunks.jsonl"

    chunk_corpus(corpus, output, word_count, target=30, maximum=40, overlap=3)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert any(row["headingPath"] == ["Beginner Guide", "Setup", "Details"] for row in rows)
    assert any("const answer = 42" in row["text"] for row in rows)
    assert all(row["sourcePath"] == "react-js-docs/guide.md" for row in rows)
    assert all(row["route"] == "/guide" for row in rows)
    assert all(row["sourceUrl"] == "https://react.dev/guide" for row in rows)
    assert all(row["sourceHash"].startswith("sha256:") for row in rows)


def test_discovers_markdown_case_insensitively_in_stable_order(tmp_path):
    corpus = tmp_path / "react-js-docs"
    corpus.mkdir()
    (corpus / "b.MDX").write_text("## B\n\nsecond", encoding="utf-8")
    (corpus / "a.md").write_text("## A\n\nfirst", encoding="utf-8")
    output = tmp_path / "chunks.jsonl"

    chunk_corpus(corpus, output, word_count)
    rows = [json.loads(line) for line in output.read_text().splitlines()]

    parents = [row for row in rows if row["recordType"] == "parent"]
    assert [row["sourcePath"] for row in parents] == ["react-js-docs/a.md", "react-js-docs/b.MDX"]


def test_rejects_invalid_size_configuration(tmp_path):
    with pytest.raises(ValueError):
        chunk_corpus(tmp_path, tmp_path / "out.jsonl", word_count, target=10, maximum=5)


def test_fenced_heading_is_not_a_section_and_children_obey_limit(tmp_path):
    corpus = tmp_path / "react-js-docs"
    corpus.mkdir()
    (corpus / "code.md").write_text(
        "# Code\n\n```python\n# This is a Python comment\n" + "value = 1\n" * 30 + "```\n",
        encoding="utf-8",
    )
    output = tmp_path / "chunks.jsonl"

    chunk_corpus(corpus, output, word_count, target=15, maximum=20, overlap=2)
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    children = [row for row in rows if row["recordType"] == "child"]

    assert all(row["headingPath"] == ["Code"] for row in rows)
    assert all(row["tokenCount"] <= 20 for row in children)
