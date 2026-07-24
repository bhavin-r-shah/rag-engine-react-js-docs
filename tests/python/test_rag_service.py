"""Dependency-free validation tests for the online RAG service."""

import pytest

from react_docs_chunker.rag.service import RAGService, _filter_children


def test_query_rejects_empty_text(tmp_path):
    with pytest.raises(ValueError, match="cannot be empty"):
        RAGService(tmp_path / "missing.jsonl").query("   ", generate_answer=False)


def test_query_rejects_invalid_top_k(tmp_path):
    with pytest.raises(ValueError, match="between 1 and 50"):
        RAGService(tmp_path / "missing.jsonl").query("question", top_k=0, generate_answer=False)


def test_query_explains_missing_offline_index(tmp_path):
    with pytest.raises(FileNotFoundError, match="offline indexing"):
        RAGService(tmp_path / "missing.jsonl").query("question", generate_answer=False)


def test_metadata_filters_are_exact_and_combined_with_and():
    children = [
        {"chunkId": "a", "docType": "reference", "contentKind": "prose", "route": "/reference/a"},
        {"chunkId": "b", "docType": "reference", "contentKind": "code", "route": "/reference/b"},
        {"chunkId": "c", "docType": "learn", "contentKind": "prose", "route": "/learn/c"},
    ]

    filtered = _filter_children(
        children, {"docType": "reference", "contentKind": "prose"}
    )

    assert [child["chunkId"] for child in filtered] == ["a"]
