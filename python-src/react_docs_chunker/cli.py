"""Command-line interface for the React documentation chunker."""

import argparse
from pathlib import Path

import tiktoken

from .chunker import chunk_corpus


def main() -> None:
    """Parse beginner-friendly command options and run the chunking pipeline."""
    parser = argparse.ArgumentParser(description="Create retrieval chunks from React Markdown files.")
    parser.add_argument("corpus", nargs="?", type=Path, default=Path("react-js-docs"))
    parser.add_argument("output", nargs="?", type=Path, default=Path("output/react-doc-chunks.jsonl"))
    parser.add_argument("--target-tokens", type=int, default=600)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--overlap-tokens", type=int, default=75)
    args = parser.parse_args()

    # cl100k_base is a practical OpenAI-family tokenizer. Counting model tokens is
    # more accurate for embedding limits than counting Python characters or words.
    encoding = tiktoken.get_encoding("cl100k_base")
    count = lambda text: len(encoding.encode(text))  # noqa: E731 - intentionally tiny adapter
    total = chunk_corpus(args.corpus.resolve(), args.output.resolve(), count, args.target_tokens, args.max_tokens, args.overlap_tokens)
    print(f"Wrote {total} parent/child records to {args.output}")


if __name__ == "__main__":
    main()
