"""OpenAI embedding backend. Requires: pip install 'react-docs-chunker[embed-openai]'"""

from __future__ import annotations

import os

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from react_docs_chunker.config import DEFAULT_OPENAI_MODEL
from react_docs_chunker.embed.embedder import EmbeddingProvider


class OpenAIEmbedder(EmbeddingProvider):
    """Calls the OpenAI embeddings API. Reads OPENAI_API_KEY from env."""

    def __init__(self, model_name: str | None = None) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable is not set")

        self._model_name = model_name or DEFAULT_OPENAI_MODEL
        self._client = OpenAI(api_key=api_key)
        self._dims: int | None = None

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        if self._dims is None:
            self._dims = len(self.embed_batch(["probe"], batch_size=1)[0])
        return self._dims

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        result: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            result.extend(self._call_api(texts[start : start + batch_size]))
        return result

    @retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(5))
    def _call_api(self, chunk: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model_name, input=chunk)
        return [item.embedding for item in response.data]
