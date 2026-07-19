"""A small, structure-aware Markdown chunker.

The implementation deliberately avoids executing or rendering MDX. Documentation is
untrusted input: this module only reads text and recognizes a few Markdown boundaries.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ANCHOR_RE = re.compile(r"\s*\{\/\*#?([\w-]+)\*\/\}\s*$")
FRONTMATTER_TITLE_RE = re.compile(r"^title:\s*[\"']?(.*?)[\"']?\s*$", re.MULTILINE)
FRONTMATTER_META_RE = re.compile(r"^meta:\s*[\"']?(.*?)[\"']?\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Section:
    """One heading and all Markdown blocks below it, up to the next heading."""

    headings: tuple[str, ...]
    anchor: str
    blocks: tuple[str, ...]


def _stable_id(*parts: str) -> str:
    """Create an ID that remains stable when unrelated files are added or removed."""
    payload = "\0".join(parts).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _clean_heading(raw: str) -> tuple[str, str]:
    """Remove React's explicit anchor comment and return (visible title, anchor)."""
    match = ANCHOR_RE.search(raw)
    anchor = match.group(1) if match else re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    title = ANCHOR_RE.sub("", raw).strip().strip("#").strip()
    return title, anchor


def _split_frontmatter(markdown: str) -> tuple[str, str | None]:
    """Separate the opening YAML block without needing a full YAML dependency."""
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return markdown, None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            yaml_text = "\n".join(lines[1:index])
            # React occasionally uses `meta` instead of `title`, so use it as the
            # second choice. Parsing only these scalar fields keeps the tool small
            # and, importantly, never constructs executable Python objects from YAML.
            match = FRONTMATTER_TITLE_RE.search(yaml_text) or FRONTMATTER_META_RE.search(yaml_text)
            return "\n".join(lines[index + 1 :]), match.group(1).strip() if match else None
    # An unmatched marker is ordinary content; silently deleting it would lose text.
    return markdown, None


def _markdown_blocks(text: str) -> list[str]:
    """Group text into paragraphs and complete fenced-code blocks.

    Blank lines normally terminate a block. A fence changes the state so blank lines
    inside an example never cause the example to be cut into invalid fragments.
    """
    blocks: list[str] = []
    current: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = stripped[:3] if stripped.startswith(("```", "~~~")) else None
        if marker and fence is None:
            fence = marker
        elif marker == fence:
            fence = None
        if not line.strip() and fence is None:
            if current:
                blocks.append("\n".join(current).strip())
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block]


def _sections(markdown: str, title: str) -> list[Section]:
    """Build sections while maintaining a breadcrumb for nested headings."""
    headings: list[str] = [title]
    current_anchor = ""
    current_lines: list[str] = []
    result: list[Section] = []

    def finish() -> None:
        if current_lines:
            result.append(Section(tuple(headings), current_anchor, tuple(_markdown_blocks("\n".join(current_lines)))))

    fence: str | None = None
    for line in markdown.splitlines():
        stripped = line.lstrip()
        marker = stripped[:3] if stripped.startswith(("```", "~~~")) else None
        # A line beginning with '#' inside a code example is source code, not a
        # documentation heading, so heading recognition is disabled inside fences.
        if marker and fence is None:
            fence = marker
        elif marker == fence:
            fence = None
        match = HEADING_RE.match(line) if fence is None and not marker else None
        if not match:
            current_lines.append(line)
            continue
        finish()
        current_lines = []
        depth = len(match.group(1))
        heading, current_anchor = _clean_heading(match.group(2))
        # Level one is the document title. Lower levels replace their breadcrumb peer.
        headings = ([heading] if depth == 1 else headings[: max(1, depth - 1)] + [heading])
    finish()
    return [section for section in result if section.blocks]


def _pack_blocks(
    blocks: tuple[str, ...], count: Callable[[str], int], target: int, maximum: int, overlap: int
) -> list[str]:
    """Pack whole Markdown blocks, then repeat complete trailing blocks as overlap."""
    chunks: list[str] = []
    current: list[str] = []
    for block in blocks:
        candidate = "\n\n".join([*current, block])
        if current and count(candidate) > target:
            chunks.append("\n\n".join(current))
            # Copy only complete blocks. This is safer than starting in the middle of code.
            carried: list[str] = []
            for old in reversed(current):
                if count("\n\n".join([old, *carried])) > overlap:
                    break
                carried.insert(0, old)
            current = carried
        current.append(block)
        # A single enormous paragraph cannot honor structure and the hard limit at once.
        # Split it by tokenizer units as the final safety valve.
        if count("\n\n".join(current)) > maximum:
            text = "\n\n".join(current)
            words = re.findall(r"\S+\s*", text)
            current = []
            piece: list[str] = []
            for word in words:
                if piece and count("".join([*piece, word])) > maximum:
                    chunks.append("".join(piece).strip())
                    piece = []
                piece.append(word)
            if piece:
                current = ["".join(piece).strip()]
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _content_kind(text: str) -> str:
    """Give downstream search code a simple prose/code filter."""
    has_code = "```" in text or "~~~" in text
    without_fences = re.sub(r"(?:```|~~~)[\s\S]*?(?:```|~~~)", "", text).strip()
    if has_code and without_fences:
        return "prose_and_code"
    return "code" if has_code else "prose"


def _source_metadata(path: Path, corpus_root: Path, raw: str) -> dict[str, str]:
    """Derive the route, URL, category, and checksum used in citations and filters."""
    relative = path.relative_to(corpus_root)
    flattened_parts = list(relative.with_suffix("").parts)
    route_parts: list[str] = []
    for part in flattened_parts:
        route_parts.extend(piece for piece in part.split("--") if piece)
    if route_parts and route_parts[-1] == "index":
        route_parts.pop()
    route = "/" + "/".join(route_parts)
    source_path = (Path(corpus_root.name) / relative).as_posix()
    return {
        "sourcePath": source_path,
        "sourceUrl": "https://react.dev" + route,
        "route": route,
        "docType": route_parts[0] if route_parts else "root",
        "sourceHash": "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }


def chunk_document(path: Path, corpus_root: Path, count: Callable[[str], int], target: int, maximum: int, overlap: int) -> list[dict]:
    """Read one document and return JSON-serializable parent and child records."""
    raw = path.read_text(encoding="utf-8")
    body, frontmatter_title = _split_frontmatter(raw)
    fallback = path.stem.split("--")[-1].replace("-", " ").title()
    title = frontmatter_title or fallback
    metadata = _source_metadata(path, corpus_root, raw)
    document_id = _stable_id(metadata["sourcePath"])
    records: list[dict] = []
    for section_number, section in enumerate(_sections(body, title)):
        parent_text = "\n\n".join(section.blocks)
        heading_path = list(section.headings)
        parent_id = _stable_id(document_id, section.anchor, parent_text)
        records.append({"recordType": "parent", "documentId": document_id, "chunkId": parent_id, **metadata, "title": title, "headingPath": heading_path, "anchor": section.anchor, "contentKind": _content_kind(parent_text), "chunkIndex": section_number, "tokenCount": count(parent_text), "text": parent_text})
        prefix = f"{' > '.join(heading_path)}\n\n"
        # The breadcrumb is part of the embedded child, so reserve its tokens when
        # packing content. This guarantees the complete record respects the limit.
        prefix_tokens = count(prefix)
        child_target = max(1, target - prefix_tokens)
        child_maximum = max(child_target, maximum - prefix_tokens)
        child_overlap = min(overlap, max(0, child_target - 1))
        for child_number, child in enumerate(_pack_blocks(section.blocks, count, child_target, child_maximum, child_overlap)):
            # Breadcrumb text makes a retrieved fragment understandable on its own.
            retrieval_text = prefix + child
            records.append({"recordType": "child", "documentId": document_id, "parentId": parent_id, "chunkId": _stable_id(parent_id, child), **metadata, "title": title, "headingPath": heading_path, "anchor": section.anchor, "contentKind": _content_kind(child), "chunkIndex": child_number, "tokenCount": count(retrieval_text), "text": retrieval_text})
    return records


def chunk_corpus(corpus: Path, output: Path, count: Callable[[str], int], target: int = 600, maximum: int = 900, overlap: int = 75) -> int:
    """Chunk every Markdown/MDX file deterministically and write newline-delimited JSON."""
    if not (0 <= overlap < target <= maximum):
        raise ValueError("expected 0 <= overlap < target <= maximum")
    # rglob also supports a future nested corpus, while sorting makes two identical
    # runs byte-for-byte reproducible regardless of filesystem traversal order.
    files = sorted(path for path in corpus.rglob("*") if path.is_file() and not path.is_symlink() and path.suffix.lower() in {".md", ".mdx"})
    records = [record for path in files for record in chunk_document(path, corpus, count, target, maximum, overlap)]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    return len(records)
