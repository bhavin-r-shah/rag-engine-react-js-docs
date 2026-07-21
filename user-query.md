# User query and answer-generation design

## Responsibility and status

The user-query stage will validate a question, obtain evidence, construct grounded
model context, and return an answer with citations. This entire stage is **proposed**;
the repository does not currently expose a query API or invoke a generative model.

## Proposed request flow

1. **Receive and validate:** require non-empty text, enforce length and request limits,
   authenticate where applicable, and treat all input as untrusted data.
2. **Normalize:** apply conservative Unicode/whitespace normalization without changing
   case-sensitive API identifiers. Optional intent detection may derive filters, but
   must retain the original question.
3. **Retrieve:** call the provider-neutral [retrieval contract](retrieval.md) with the
   validated question and permitted filters.
4. **Assemble context:** select evidence within the generator token budget, preserve
   code fences and breadcrumbs, deduplicate repeated parent material, and assign stable
   citation labels tied to record IDs and URLs.
5. **Generate:** instruct a model to answer only from supplied evidence, distinguish
   version-sensitive facts, cite supporting sections, and say when evidence is
   insufficient. Model integration remains behind an interface.
6. **Validate response:** ensure emitted citations resolve to supplied records and
   remove or reject unsupported citation identifiers. Never execute generated or
   retrieved code.
7. **Return:** provide the answer, citations, and safe request metadata; stream only if
   citation validation remains possible before final completion.

## Context and citation shape

Each context item should include a citation ID, child text, optional expanded parent
text, title, heading path, source URL, anchor, and content kind. Citation rendering
uses only this map; the model cannot introduce an arbitrary URL. Context ordering
follows retrieval rank while enforcing configurable source and parent diversity.

## Failure behavior and observability

- Invalid requests return a clear client error without calling retrieval.
- No or low-confidence evidence returns an explicit insufficient-evidence response.
- Retrieval, embedding, or generation timeouts are bounded and classified separately.
- Provider failures must not expose secrets, stack traces, or raw internal prompts.
- Record latency by stage, result counts, token use, citation validation, refusal rate,
  and provider errors. Avoid logging full questions, source bodies, or generated answers
  unless an explicit privacy-reviewed retention policy permits it.

Online feedback must not silently modify ranking or prompts. Feed reviewed failures
into the version-controlled retrieval evaluation set instead.
