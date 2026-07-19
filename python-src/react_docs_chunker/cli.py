"""Command-line interface for the React documentation chunker.

This module is the thin layer between commands typed in a terminal and the reusable
functions in :mod:`react_docs_chunker.chunker`. It does not implement chunking itself:
it reads options, creates a token-counting function, and calls ``chunk_corpus``.
"""

# argparse is part of Python's standard library. It turns terminal text such as
# ``--max-tokens 900`` into typed Python values and automatically provides ``--help``.
import argparse

# Path represents filesystem paths in an operating-system-independent way, avoiding
# manual handling of Windows backslashes versus macOS/Linux forward slashes.
from pathlib import Path

# tiktoken is the one runtime dependency. It counts the same style of text units
# (tokens) used by AI models, which is more useful than counting characters.
import tiktoken

from .chunker import chunk_corpus
from .config import MAX_TOKENS, OVERLAP_TOKENS, TARGET_TOKENS, TOKENIZER_ENCODING


def main() -> None:
    """Parse terminal options, run the chunker, and report where output was written."""
    # ArgumentParser owns the usage text printed by the ``--help`` option.
    parser = argparse.ArgumentParser(description="Create retrieval chunks from React Markdown files.")
    # ``nargs='?'`` makes each path optional. If it is omitted, argparse uses the
    # default beside it. ``type=Path`` converts terminal strings into Path objects.
    parser.add_argument("corpus", nargs="?", type=Path, default=Path("react-js-docs"))
    parser.add_argument("output", nargs="?", type=Path, default=Path("output/react-doc-chunks.jsonl"))
    # These flags override config.py for only this execution; they do not edit files.
    parser.add_argument("--target-tokens", type=int, default=TARGET_TOKENS)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--overlap-tokens", type=int, default=OVERLAP_TOKENS)
    args = parser.parse_args()  # Read and validate the values typed by the user.

    # cl100k_base is a practical OpenAI-family tokenizer. Counting model tokens is
    # more accurate for embedding limits than counting Python characters or words.
    encoding = tiktoken.get_encoding(TOKENIZER_ENCODING)
    # A lambda is a short unnamed function. Here, ``count('hello')`` encodes the text
    # and returns the number of resulting tokens. The chunker accepts this function
    # as an argument, which keeps it independent from any particular AI tokenizer.
    count = lambda text: len(encoding.encode(text))  # noqa: E731 - intentionally tiny adapter
    # resolve() changes relative paths into unambiguous absolute paths before work
    # begins. chunk_corpus returns the number of JSONL records it wrote.
    total = chunk_corpus(args.corpus.resolve(), args.output.resolve(), count, args.target_tokens, args.max_tokens, args.overlap_tokens)
    print(f"Wrote {total} parent/child records to {args.output}")


# Python sets __name__ to "__main__" only when this file is executed as a program.
# The guard prevents the CLI from running unexpectedly when another module imports it.
if __name__ == "__main__":
    main()
