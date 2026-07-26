# User query and answer generation

## Browser UI

Start the local server with:

```bash
python -m react_docs_chunker.ui.app
```

The page at `http://127.0.0.1:8000` separates online controls (used every question)
from one-time offline index settings, so a beginner can see that chunking, embedding,
and vector-database choice do not run for every question:

| Online control | Meaning |
| --- | --- |
| `Top K` | Maximum number of retrieved chunks to return, from 1 to 50. |
| `Hybrid` | Combines semantic dense search and exact-word BM25 ranking (see [`retrieval.md`](retrieval.md)). |
| `Dense` | Uses a fresh query embedding to find semantically similar chunks. |
| `BM25` | Uses keyword matching and does not embed the query. |
| `Document type` | Limits results to one corpus category, such as `learn`, `reference`, or `blog`. |
| `Content` | Limits results to `prose`, `code`, or `prose_and_code`. |
| `Exact route` | Limits results to one React documentation route. |
| `Generate an LLM answer` | Calls the chat model when selected; otherwise only retrieved evidence is shown. |

The three metadata filters are optional and combined with **AND**; filter choices come
from the active JSONL index. The active embedding provider and vector database are
shown as read-only, since both must match whatever was used to build the index —
change them in the offline setup panel and rebuild instead.

## Per-question flow

1. Validate the non-empty question and Top K range.
2. Build BM25 when required and/or embed the query afresh for dense retrieval.
3. Apply selected metadata filters, search the active vector store (whichever backend
   the manifest names), and fuse hybrid rankings.
4. Resolve each child's parent from JSONL and create citation IDs and source links.
5. When answer generation is enabled, send only the question and retrieved evidence
   to the configured OpenAI chat model.
6. Reject an answer that uses citation labels not supplied in the context.
7. Return the answer, model details, retrieved chunks, scores, and citations as JSON.

The default generation model is `gpt-4o-mini`; set `OPENAI_CHAT_MODEL` to choose
another model available to the configured account. Clear **Generate an LLM answer**
to perform retrieval without a generation API call.

The server binds to `127.0.0.1` by default and is intended for local learning. It does
not implement user authentication, request quotas, or production deployment controls.
