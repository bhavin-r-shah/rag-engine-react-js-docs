"""BM25 keyword index built from child records (in-memory, rebuilt at search startup)."""

from __future__ import annotations

from rank_bm25 import BM25Okapi


class BM25Store:
    def __init__(self) -> None:
        self._index = None
        self._chunk_ids: list[str] = []
        self._records: list[dict] = []

    def build(self, records: list[dict]) -> None:
        self._records = records
        self._chunk_ids = [r["chunkId"] for r in records]
        tokenized = [r["text"].lower().split() for r in records]
        self._index = BM25Okapi(tokenized)

    def query(self, query_text: str, n_results: int = 10) -> list[dict]:
        if self._index is None:
            raise RuntimeError("Call build() before query()")
        tokens = query_text.lower().split()
        scores = self._index.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        results = []
        for rank_idx in ranked[:n_results]:
            rec = self._records[rank_idx]
            results.append({
                "chunkId": rec["chunkId"],
                "score": float(scores[rank_idx]),
                "text": rec["text"],
                "metadata": {k: v for k, v in rec.items() if k not in ("text", "chunkId")},
            })
        return results
