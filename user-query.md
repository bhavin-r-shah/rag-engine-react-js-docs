# User query and answer generation

## Browser UI

Start the local server with:

```bash
python -m react_docs_chunker.ui.app
```

The page at `http://127.0.0.1:8000` provides online controls for Top K, dense/BM25/
hybrid search, document type, content kind, and exact route. It also displays the active
embedding provider as read-only and keeps the one-time offline index
settings separately so a beginner can see that chunking and document embedding do not
run for every question.

## Per-question flow

1. Validate the non-empty question and Top K range.
2. Build BM25 when required and/or embed the query afresh for dense retrieval.
3. Apply selected metadata filters, search the active Chroma collection, and fuse
   hybrid rankings.
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
