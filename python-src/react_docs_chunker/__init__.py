"""Public entry points for the React documentation chunker.

Python treats every directory containing an ``__init__.py`` file as an importable
package. This file intentionally exposes only the two functions most callers need,
so users do not have to know how the internal helper modules are organized.
"""

# The leading dot means "import from this same package." A corpus is the whole
# directory of documents; a document is one Markdown or MDX file.
from .chunker import chunk_corpus, chunk_document

# ``__all__`` documents the supported public API and controls what is imported by
# ``from react_docs_chunker import *``. Most Python programs should still import the
# two names explicitly because explicit imports are easier for beginners to follow.
__all__ = ["chunk_corpus", "chunk_document"]
