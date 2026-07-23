"""Small local browser UI for offline index setup and online RAG questions."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from react_docs_chunker.rag.service import RAGService

HTML_PATH = Path(__file__).with_name("index.html")
MANIFEST_PATH = Path("output/index_manifest.json")


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
            self._json({"ready": manifest is not None, "manifest": manifest})
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
                    data.get("query", ""), int(data.get("topK", 5)),
                    data.get("searchMode", "hybrid"), data.get("embedder", "local"),
                    bool(data.get("generateAnswer", True)),
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
