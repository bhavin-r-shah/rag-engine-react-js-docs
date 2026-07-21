"""Provider-agnostic embedding contract."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @abstractmethod
    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]: ...
