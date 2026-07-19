# Chunking design

## Responsibility and status

Chunking turns a long document into smaller pieces that an AI search system can find.
This design uses two kinds of output records:

- A **parent** stores one complete Markdown section.
- A **child** stores a smaller, searchable piece of that parent.

In this project, **one child is one searchable chunk**. The words *child* and
*retrieval chunk* therefore mean the same thing in this document. A parent is stored
so the application can load the complete section after it finds a child.

This two-step strategy is **implemented** in
[`chunker.py`](python-src/react_docs_chunker/chunker.py): first find sections from
headings, then split a section only when it is too large.

## Beginner glossary

| Term | Simple meaning |
| --- | --- |
| Document | One complete Markdown or MDX file. |
| Heading | A Markdown title such as `## Installation`. |
| Section | A heading and the content below it, stopping at the next heading. |
| Parent | The stored record containing the complete section. |
| Child or retrieval chunk | A smaller piece used by AI search. **One child equals one searchable chunk.** |
| Breadcrumb | The heading path added to a child, such as `Hooks > useEffect > Parameters`. |
| Token | A small unit of text counted by the AI tokenizer; it is not always a whole word. |
| Overlap | A small amount of repeated content that gives neighboring chunks shared context. |

## Phase 1: headings create sections

[`HEADING_RE`](python-src/react_docs_chunker/chunker.py#L37) recognizes Markdown ATX
headings with one through six leading `#` characters followed by whitespace. Thus
`#`, `##`, `###`, `####`, `#####`, and `######` each start a new section. A heading
without whitespace (such as `##Setup`) and an indented heading do not match this
deliberately small scanner.

[`_sections`](python-src/react_docs_chunker/chunker.py#L117-L149) scans line by line.
Fence state at [lines 128–138](python-src/react_docs_chunker/chunker.py#L128-L138)
prevents `#` inside a fenced code example from becoming a documentation section. On a
real heading, the scanner finishes the preceding section, cleans its title and React
anchor, and updates the breadcrumb:

- `#` replaces the breadcrumb with that level-one document heading.
- A deeper heading retains the available ancestors, replaces any peer at its level,
  and appends itself, as implemented at
  [lines 142–147](python-src/react_docs_chunker/chunker.py#L142-L147).
- Consequently, `##` and `###` both create separate parent sections; they do not merely
  annotate the content before them.

Before this scan, front matter supplies the initial title when available, otherwise
the filename supplies a fallback. The call is made at
[`chunk_document` lines 225–235](python-src/react_docs_chunker/chunker.py#L225-L235).
Each non-empty completed section becomes a parent record at
[lines 238–243](python-src/react_docs_chunker/chunker.py#L238-L243).

## How sections relate to chunks

The short answer is: **yes, one child equals one searchable chunk**. However, one
section does not always equal one child. The relationship is:

```text
one non-empty Markdown section
        |
        +-- one parent record that stores the complete section
        |
        +-- one child / searchable chunk, when the section is small enough
        |
        `-- multiple children / searchable chunks, when the section is too large
```

Every non-empty section creates exactly one parent. If the section is small enough, it
also creates one child. If the section is too large, it creates two or more children.
The complete parent is kept even when it is larger than the child size limit.

AI search uses the children. When search finds a child, its `parentId` tells the
application which complete parent section it came from. Parent and child record
construction can be seen at
[`chunk_document` lines 238–253](python-src/react_docs_chunker/chunker.py#L238-L253).

For example:

- A short `Caveats` section may create **one parent and one child**. That means it has
  one searchable chunk.
- A long `Parameters` section may create **one parent and three children**. That means
  it has three searchable chunks, and all three point to the same parent.

The exact number of children depends on the heading breadcrumb, paragraph and code
block sizes, token limits, and overlap. It is not calculated by simply dividing the
section's token count by the target size.

Headings with no content before the next heading do not produce an empty parent or
child: `_sections` filters out sections without blocks at
[`chunker.py` line 149](python-src/react_docs_chunker/chunker.py#L149). Content before
the first Markdown heading, if present, belongs to the initial document-title section.

| Section size | Parent records | Child records | Search behavior |
| --- | ---: | ---: | --- |
| Empty | 0 | 0 | Nothing is indexed. |
| Small enough | 1 | 1 | Search can find one child, which is one searchable chunk. |
| Too large | 1 | 2 or more | Search finds smaller chunks; `parentId` leads back to the complete section. |

### Section example

Given:

````markdown
# Hooks

Introductory text.

## useEffect

Effect overview.

### Parameters

First parameter paragraph.

Second parameter paragraph.

```js
useEffect(() => {
  connect();
}, []);
```

### Caveats

Caveat text.
````

Phase 1 produces these semantic sections. Each row becomes one parent; with normal
600-token defaults, each small row also becomes one child:

| Heading path | Parent content |
| --- | --- |
| `Hooks` | `Introductory text.` |
| `Hooks > useEffect` | `Effect overview.` |
| `Hooks > useEffect > Parameters` | Both parameter paragraphs and the complete code fence. |
| `Hooks > useEffect > Caveats` | `Caveat text.` |

The existing test verifies nested breadcrumbs, explicit anchors, and preserved code in
[`test_chunks_nested_headings_and_preserves_code`](tests/python/test_chunker.py#L20-L50).

## Phase 2: oversized sections create children

Section content is first converted into blank-line-separated blocks by
[`_markdown_blocks`](python-src/react_docs_chunker/chunker.py#L90-L114). Fence state
keeps a complete fenced example—including its internal blank lines—in one block.

[`_pack_blocks`](python-src/react_docs_chunker/chunker.py#L152-L186) then packs whole
blocks in order:

1. It appends blocks while the candidate stays within the target.
2. If another block crosses the target, it emits the accumulated child at
   [lines 159–162](python-src/react_docs_chunker/chunker.py#L159-L162).
3. It carries only complete trailing blocks that fit the overlap allowance into the
   next child at [lines 162–168](python-src/react_docs_chunker/chunker.py#L162-L168).
4. If one indivisible block exceeds the hard maximum, the final safety valve at
   [lines 170–183](python-src/react_docs_chunker/chunker.py#L170-L183) splits on
   whitespace-delimited units. This can split a structurally indivisible paragraph or
   fenced block and is used only to enforce the hard limit.

Each child embeds its heading breadcrumb. The code reserves those prefix tokens before
calculating the content target, maximum, and overlap at
[`chunk_document` lines 243–250](python-src/react_docs_chunker/chunker.py#L243-L250),
so the complete retrieval text—not only its body—obeys the maximum.

### Oversized-section example

Assume illustrative limits of **20 target tokens**, **30 maximum tokens**, and enough
overlap for one short paragraph. These are intentionally small teaching values, not
the repository defaults. For the `Parameters` section above, blank lines create three
blocks: the first paragraph, the second paragraph, and the complete JavaScript fence.

An illustrative packing result is:

````text
child 1
Hooks > useEffect > Parameters

First parameter paragraph.

Second parameter paragraph.

child 2
Hooks > useEffect > Parameters

Second parameter paragraph.       <- complete trailing-block overlap

```js
useEffect(() => {
  connect();
}, []);
```
````

Exact membership depends on tokenizer counts, but the invariant does not: splitting
occurs between complete blocks whenever possible, overlap never crosses a section
boundary, and every child receives the breadcrumb.

Now consider one paragraph containing more than 30 tokens with no blank line. It is
one block, so there is no safe block boundary. The maximum-size safety valve divides
its whitespace-delimited units into pieces of at most the available maximum. This is
less structurally desirable than block packing, but prevents an unbounded child.

The fenced-heading and child-limit behavior is covered by
[`test_fenced_heading_is_not_a_section_and_children_obey_limit`](tests/python/test_chunker.py#L74-L89).

## Configuration

Defaults live in [`config.py`](python-src/react_docs_chunker/config.py): heading-first
chunking is enabled, the target is 600 tokens, the hard maximum is 900, overlap is 75,
and the tokenizer encoding is `cl100k_base`. CLI flags may override the three numeric
values for one run. [`chunk_corpus`](python-src/react_docs_chunker/chunker.py#L271-L272)
requires `0 <= overlap < target <= maximum`.
