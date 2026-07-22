"""Local embedding via sentence-transformers. Requires: pip install 'react-docs-chunker[embed]'"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from react_docs_chunker.config import DEFAULT_LOCAL_MODEL
from react_docs_chunker.embed.embedder import EmbeddingProvider


class SentenceTransformerEmbedder(EmbeddingProvider):
    """Downloads model to ~/.cache/ on first use. No API key or rate limiting needed."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or DEFAULT_LOCAL_MODEL
        self._model = SentenceTransformer(self._model_name)

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._model.get_embedding_dimension()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        vectors = self._model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        return [v.tolist() for v in vectors]
