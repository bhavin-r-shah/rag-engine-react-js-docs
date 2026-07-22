"""SQLite-backed embedding cache keyed by (model_id, text)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from react_docs_chunker.config import EMBED_CACHE_PATH


class EmbedCache:
    def __init__(self, db_path: str | Path | None = None) -> None:
        path = Path(db_path or EMBED_CACHE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS embeddings"
            " (cache_key TEXT PRIMARY KEY, vector TEXT NOT NULL)"
        )
        self._conn.commit()

    @staticmethod
    def _key(model_id: str, text: str) -> str:
        return hashlib.sha256(f"{model_id}\x00{text}".encode()).hexdigest()

    def get(self, model_id: str, text: str) -> list[float] | None:
        row = self._conn.execute(
            "SELECT vector FROM embeddings WHERE cache_key = ?",
            (self._key(model_id, text),),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, model_id: str, text: str, vector: list[float]) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO embeddings (cache_key, vector) VALUES (?, ?)",
            (self._key(model_id, text), json.dumps(vector)),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
