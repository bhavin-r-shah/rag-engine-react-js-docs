"""Provider-neutral contract for turning retrieved evidence into an answer."""
from __future__ import annotations

from abc import ABC, abstractmethod


class GenerationProvider(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @abstractmethod
    def generate(self, question: str, context: list[dict]) -> str: ...
