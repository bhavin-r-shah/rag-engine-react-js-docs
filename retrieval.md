# Retrieval design

## Responsibility and status

Retrieval will turn a validated user search query into ranked, traceable evidence for
answer generation. Dense search, lexical search, fusion, reranking, and parent hydration
are all **proposed** and are not implemented in the current Python package.

## Proposed retrieval pipeline

1. Accept normalized query text and optional filters from the
   [user-query stage](user-query.md).
2. Generate dense candidates from the query embedding against the compatible child
   vector index.
3. Generate lexical/BM25 candidates for exact identifiers, props, error numbers, and
   phrases.
4. Apply allowed filters such as route, document type, heading path, content kind, or
   publication date in candidate generation where supported.
5. Fuse dense and lexical rankings using a configured, evaluation-backed algorithm
   such as reciprocal-rank fusion. Do not compare raw scores from unlike systems as if
   they shared a scale.
6. Optionally rerank a bounded candidate set with a provider-neutral reranker.
7. Deduplicate by child ID, control repeated evidence from the same parent, and hydrate
   selected parents when broader section context is required.
8. Return ordered evidence with child text, parent content when requested, source URL,
   route, title, heading path, anchor, scores, and retrieval-method diagnostics.

Candidate counts, fusion constants, metadata boosts, parent diversity, and reranking
depth are configuration—not hard-coded assumptions.

## Citation and failure contract

Every result must retain a resolvable source URL and enough heading/anchor metadata to
construct a section-level citation. Missing provenance is a validation failure, not a
reason to invent a citation. If one retrieval backend is temporarily unavailable, a
documented degraded mode may use the other backend and label telemetry accordingly;
if trustworthy evidence is insufficient, the query layer must decline to fabricate an
answer.

## Evaluation

Maintain a version-controlled golden dataset covering conceptual learning questions,
exact API lookups, code examples, warnings/errors, React Server Components,
version-sensitive blog facts, and similar identifiers requiring disambiguation. Each
case records acceptable routes, anchors, and expected facts.

Compare dense-only, lexical-only, hybrid, and reranked variants using recall at K,
mean reciprocal rank, section-level citation accuracy, latency, and cost. Use these
results to select chunk limits and retrieval configuration.
