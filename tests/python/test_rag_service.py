"""Dependency-free validation tests for the online RAG service."""

import pytest

from react_docs_chunker.rag.service import RAGService


def test_query_rejects_empty_text(tmp_path):
    with pytest.raises(ValueError, match="cannot be empty"):
        RAGService(tmp_path / "missing.jsonl").query("   ", generate_answer=False)


def test_query_rejects_invalid_top_k(tmp_path):
    with pytest.raises(ValueError, match="between 1 and 50"):
        RAGService(tmp_path / "missing.jsonl").query("question", top_k=0, generate_answer=False)


def test_query_explains_missing_offline_index(tmp_path):
    with pytest.raises(FileNotFoundError, match="offline indexing"):
        RAGService(tmp_path / "missing.jsonl").query("question", generate_answer=False)
