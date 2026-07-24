"""Small local browser UI for offline index setup and online RAG questions."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from react_docs_chunker.rag.service import RAGService

HTML_PATH = Path(__file__).with_name("index.html")
MANIFEST_PATH = Path("output/index_manifest.json")
JSONL_PATH = Path("output/react-doc-chunks.jsonl")


def _facets() -> dict[str, list[str]]:
    values = {"docTypes": set(), "contentKinds": set(), "routes": set()}
    if JSONL_PATH.exists():
        for line in JSONL_PATH.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("recordType") != "child":
                continue
            values["docTypes"].add(record.get("docType", ""))
            values["contentKinds"].add(record.get("contentKind", ""))
            values["routes"].add(record.get("route", ""))
    return {key: sorted(value for value in items if value) for key, items in values.items()}


class Handler(BaseHTTPRequestHandler):
    def _json(self, value: dict, status: int = 200) -> None:
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/status":
            manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else None
            self._json({
                "ready": manifest is not None and JSONL_PATH.exists(),
                "manifest": manifest,
                "facets": _facets(),
            })
            return
        if self.path in {"/", "/index.html"}:
            body = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/query":
                result = RAGService().query(
                    query_text=data.get("query", ""),
                    top_k=int(data.get("topK", 5)),
                    search_mode=data.get("searchMode", "hybrid"),
                    generate_answer=bool(data.get("generateAnswer", True)),
                    doc_type=data.get("docType", ""),
                    content_kind=data.get("contentKind", ""),
                    route=data.get("route", ""),
                )
                self._json(result)
                return
            if self.path == "/api/index":
                from react_docs_chunker.indexing.pipeline import build_index

                result = build_index(
                    "react-js-docs", "output/react-doc-chunks.jsonl",
                    data.get("embedder", "local"), data.get("chunkingMethod", "markdown"),
                    int(data.get("targetTokens", 600)), int(data.get("maxTokens", 900)),
                    int(data.get("overlapTokens", 75)),
                )
                self._json(result)
                return
            self._json({"error": "Unknown endpoint"}, 404)
        except Exception as exc:
            self._json({"error": str(exc)}, 400)

    def log_message(self, format: str, *args) -> None:
        print(f"UI: {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local React docs RAG UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Open http://{args.host}:{args.port} in a browser")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nUI stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
