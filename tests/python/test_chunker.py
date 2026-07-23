"""Automated examples that verify the chunker behaves as documented.

pytest discovers functions whose names begin with ``test_``. Each test builds a tiny
temporary corpus, runs real chunking code, and uses ``assert`` to describe the expected
result. pytest deletes ``tmp_path`` automatically after the test.
"""

import json

import pytest

from react_docs_chunker.chunker import chunk_corpus


def word_count(text: str) -> int:
    """A dependency-free test counter; production uses the tiktoken tokenizer."""
    return len(text.split())


def test_chunks_nested_headings_and_preserves_code(tmp_path):
    """Titles, breadcrumbs, code, routes, URLs, and hashes survive processing."""
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

    # Tiny limits force the sample through the splitting path without a huge fixture.
    chunk_corpus(corpus, output, word_count, target=30, maximum=40, overlap=3)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert any(row["headingPath"] == ["Beginner Guide", "Setup", "Details"] for row in rows)
    assert any("const answer = 42" in row["text"] for row in rows)
    assert all(row["sourcePath"] == "react-js-docs/guide.md" for row in rows)
    assert all(row["route"] == "/guide" for row in rows)
    assert all(row["sourceUrl"] == "https://react.dev/guide" for row in rows)
    assert all(row["sourceHash"].startswith("sha256:") for row in rows)


def test_discovers_markdown_case_insensitively_in_stable_order(tmp_path):
    """Both .md and uppercase .MDX files are accepted and alphabetically ordered."""
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
    """A hard maximum smaller than the target is rejected with a clear exception."""
    with pytest.raises(ValueError):
        chunk_corpus(tmp_path, tmp_path / "out.jsonl", word_count, target=10, maximum=5)


def test_fenced_heading_is_not_a_section_and_children_obey_limit(tmp_path):
    """A '#' inside Python example code is not mistaken for a Markdown heading."""
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


def test_fixed_chunking_uses_length_and_overlap(tmp_path):
    corpus = tmp_path / "react-js-docs"
    corpus.mkdir()
    (corpus / "guide.md").write_text(
        "one two three four five six seven eight nine ten", encoding="utf-8"
    )
    output = tmp_path / "chunks.jsonl"

    chunk_corpus(corpus, output, word_count, target=6, maximum=6, overlap=2, method="fixed")
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    children = [row for row in rows if row["recordType"] == "child"]

    assert len(children) >= 2
    assert all(row["tokenCount"] <= 6 for row in children)
    first_body = children[0]["text"].split("\n\n", 1)[1]
    second_body = children[1]["text"].split("\n\n", 1)[1]
    assert set(first_body.split()) & set(second_body.split())


def test_recursive_chunking_prefers_paragraph_boundaries(tmp_path):
    corpus = tmp_path / "react-js-docs"
    corpus.mkdir()
    (corpus / "guide.md").write_text(
        "First short paragraph.\n\nSecond short paragraph.\n\nThird short paragraph.",
        encoding="utf-8",
    )
    output = tmp_path / "chunks.jsonl"

    chunk_corpus(corpus, output, word_count, target=7, maximum=7, overlap=0, method="recursive")
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    children = [row for row in rows if row["recordType"] == "child"]

    assert len(children) >= 2
    assert all(row["tokenCount"] <= 7 for row in children)
    assert any("First short paragraph" in row["text"] for row in children)


def test_unknown_chunking_method_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="method must be one of"):
        chunk_corpus(tmp_path, tmp_path / "out.jsonl", word_count, method="unknown")
