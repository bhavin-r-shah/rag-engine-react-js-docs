"""Reusable online RAG query service used by both the CLI and browser UI."""
from __future__ import annotations

import json
import re
from pathlib import Path

from react_docs_chunker.config import EMBED_CACHE_PATH, JSONL_PATH
from react_docs_chunker.embed.cache import EmbedCache
from react_docs_chunker.search.engine import load_parents


def _load_children(path: str | Path) -> list[dict]:
    return [
        record
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and (record := json.loads(line)).get("recordType") == "child"
    ]


def _filter_children(children: list[dict], filters: dict[str, str]) -> list[dict]:
    """Apply exact-match metadata filters before BM25 or hybrid ranking."""
    return [
        child for child in children
        if all(child.get(key) == value for key, value in filters.items())
    ]


class RAGService:
    """Loads the offline index and performs a fresh online search for every query."""

    def __init__(
        self, jsonl_path: str | Path = JSONL_PATH,
        manifest_path: str | Path = "output/index_manifest.json",
    ) -> None:
        self.jsonl_path = Path(jsonl_path)
        self.manifest_path = Path(manifest_path)

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        search_mode: str = "hybrid",
        embedder_name: str | None = None,
        generate_answer: bool = True,
        doc_type: str = "",
        content_kind: str = "",
        route: str = "",
    ) -> dict:
        query_text = query_text.strip()
        if not query_text:
            raise ValueError("Query cannot be empty")
        if not 1 <= top_k <= 50:
            raise ValueError("Top K must be between 1 and 50")
        if search_mode not in {"dense", "bm25", "hybrid"}:
            raise ValueError("Search mode must be dense, bm25, or hybrid")
        if not self.jsonl_path.exists():
            raise FileNotFoundError("Chunk JSONL is missing. Run the offline indexing step first.")
        if not self.manifest_path.exists():
            raise FileNotFoundError("Index manifest is missing. Run the offline indexing step first.")

        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        active_embedder = manifest["embedder"]
        if embedder_name and embedder_name != active_embedder:
            raise ValueError(
                f"The active index uses '{active_embedder}', not '{embedder_name}'. Rebuild the index to change embedders."
            )
        metadata_filters = {
            key: value
            for key, value in {
                "docType": doc_type.strip(),
                "contentKind": content_kind.strip(),
                "route": route.strip(),
            }.items()
            if value
        }

        from react_docs_chunker.search.bm25 import BM25Store
        from react_docs_chunker.search.engine import bm25_search, dense_search, hybrid_search

        children = _load_children(self.jsonl_path)
        filtered_children = _filter_children(children, metadata_filters)
        if not filtered_children:
            return {
                "query": query_text, "searchMode": search_mode, "topK": top_k,
                "embeddingModel": manifest.get("embeddingModel"),
                "generationModel": None,
                "answer": "No indexed chunks matched the selected filters.",
                "citations": [], "filters": metadata_filters,
            }
        bm25 = None
        embedder = store = cache = None
        if search_mode in {"bm25", "hybrid"}:
            bm25 = BM25Store()
            bm25.build(filtered_children)
        if search_mode in {"dense", "hybrid"}:
            from react_docs_chunker._cli_utils import build_embedder, build_vector_store

            embedder = build_embedder(active_embedder)
            store = build_vector_store(
                "chroma", embedder, collection_name=manifest.get("collectionName")
            )
            cache = EmbedCache(EMBED_CACHE_PATH)

        if search_mode == "dense":
            results = dense_search(
                query_text, embedder, cache, store, n=top_k,
                metadata_filters=metadata_filters,
            )
        elif search_mode == "bm25":
            results = bm25_search(query_text, bm25, n=top_k)
        else:
            results = hybrid_search(
                query_text, embedder, cache, store, bm25, n=top_k,
                metadata_filters=metadata_filters,
            )

        parents = load_parents(self.jsonl_path)
        citations = []
        for index, result in enumerate(results, 1):
            metadata = result.get("metadata") or {}
            parent = parents.get(metadata.get("parentId", ""), {})
            source_url = metadata.get("sourceUrl", "")
            anchor = metadata.get("anchor", "")
            citation_url = source_url + (f"#{anchor}" if anchor and "#" not in source_url else "")
            citations.append({
                "citationId": f"S{index}",
                "chunkId": result.get("chunkId", ""),
                "parentId": metadata.get("parentId", ""),
                "title": metadata.get("title", parent.get("title", "React documentation")),
                "headingPath": parent.get("headingPath", []),
                "route": metadata.get("route", ""),
                "citationUrl": citation_url,
                "text": result.get("text", ""),
                "parentText": parent.get("text", ""),
                "score": next((result[key] for key in ("rrf_score", "score", "distance") if key in result), None),
            })

        answer = "Answer generation is disabled. Review the retrieved chunks below."
        generation_model = None
        if generate_answer:
            from react_docs_chunker.generation.openai_generator import OpenAIGenerator

            generator = OpenAIGenerator()
            answer = generator.generate(query_text, citations)
            generation_model = generator.model_id
            valid = {item["citationId"] for item in citations}
            used = set(re.findall(r"\[(S\d+)\]", answer))
            invalid = used - valid
            if invalid:
                raise ValueError(f"The generated answer contained invalid citations: {sorted(invalid)}")

        return {
            "query": query_text,
            "searchMode": search_mode,
            "topK": top_k,
            "embeddingModel": getattr(embedder, "model_id", None),
            "generationModel": generation_model,
            "answer": answer,
            "citations": citations,
            "filters": metadata_filters,
        }
