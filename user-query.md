# User query design

## Responsibility and status

PR #8 implements a **terminal search query**, not a full chatbot question-and-answer
stage. A user supplies a non-empty positional string to the search CLI, which retrieves
and prints ranked child-chunk previews.

## Implemented flow

1. Activate the project virtual environment.
2. Enter a quoted query, for example:

   ```bash
   python -m react_docs_chunker.search.cli "When should I use useMemo?" --mode hybrid --n 5
   ```

3. `argparse` reads the query, mode, provider, vector database, JSONL path, and result
   count.
4. Dense or hybrid mode embeds and caches the query, then searches ChromaDB. BM25 or
   hybrid mode builds a keyword index from JSONL.
5. The CLI prints ranked routes, scores, and short text previews.

Quotes keep a multi-word question as one command-line argument. The `--n` value
controls the number of displayed results. The query embedding cache uses the same
SQLite cache as document embeddings.

## Is there a UI or generated answer?

**No.** There is no browser UI, React query form, HTTP API, or chat screen in the
current repository. The terminal is the user interface. The program retrieves source
chunks but does not pass them to a large language model, write a natural-language
answer, or validate and render citations.

A future answer-generation layer would need input limits, context assembly, parent
hydration, a model adapter, grounded-answer instructions, citation validation, privacy
controls, and clear insufficient-evidence behavior. None of those should be described
as implemented yet.
