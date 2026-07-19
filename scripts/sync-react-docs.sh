#!/usr/bin/env bash

set -euo pipefail

readonly UPSTREAM_REPOSITORY="https://github.com/reactjs/react.dev.git"
readonly UPSTREAM_CONTENT_PATH="src/content"
readonly REACT_DOCS_REF="${REACT_DOCS_REF:-main}"

repository_root="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
temporary_directory="$(mktemp -d "${TMPDIR:-/tmp}/react-docs.XXXXXX")"
trap 'rm -rf "$temporary_directory"' EXIT

checkout_directory="$temporary_directory/react.dev"
staged_docs_directory="$temporary_directory/react-js-docs"

echo "Fetching React documentation at ${REACT_DOCS_REF}..."
git init --quiet "$checkout_directory"
git -C "$checkout_directory" remote add origin "$UPSTREAM_REPOSITORY"
git -C "$checkout_directory" sparse-checkout set "$UPSTREAM_CONTENT_PATH"
git -C "$checkout_directory" fetch --quiet --depth 1 --filter=blob:none origin "$REACT_DOCS_REF"
git -C "$checkout_directory" checkout --quiet --detach FETCH_HEAD

mkdir -p "$staged_docs_directory"
source_directory="$checkout_directory/$UPSTREAM_CONTENT_PATH"

while IFS= read -r -d '' source_file; do
  relative_path="${source_file#"$source_directory/"}"
  flattened_filename="${relative_path//\//--}"
  destination_file="$staged_docs_directory/$flattened_filename"

  if [[ -e "$destination_file" ]]; then
    echo "Flattened filename collision: $relative_path maps to $flattened_filename" >&2
    exit 1
  fi

  cp "$source_file" "$destination_file"
done < <(find "$source_directory" -type f \( -iname '*.md' -o -iname '*.mdx' \) -print0)

file_count="$(find "$staged_docs_directory" -type f | wc -l | tr -d ' ')"
if [[ "$file_count" == "0" ]]; then
  echo "No Markdown files were found at $UPSTREAM_CONTENT_PATH" >&2
  exit 1
fi

git -C "$checkout_directory" rev-parse HEAD > "$staged_docs_directory/.react-docs-commit"

rm -rf "$repository_root/react-js-docs"
mv "$staged_docs_directory" "$repository_root/react-js-docs"

echo "Copied $file_count Markdown files into $repository_root/react-js-docs"
