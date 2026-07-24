"""Vector store abstraction shared by all backends."""

from __future__ import annotations

from abc import ABC, abstractmethod


class VectorStore(ABC):
    @abstractmethod
    def upsert_chunks(self, records: list[dict], embeddings: list[list[float]]) -> None: ...

    @abstractmethod
    def query_dense(
        self, query_embedding: list[float], n_results: int,
        metadata_filters: dict[str, str] | None = None,
    ) -> list[dict]: ...

    @abstractmethod
    def query_hybrid(
        self, query_text: str, query_embedding: list[float], n_results: int
    ) -> list[dict]: ...

    @abstractmethod
    def close(self) -> None: ...

