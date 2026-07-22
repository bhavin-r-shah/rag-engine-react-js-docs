"""Default chunking strategy settings.

This is the first file to edit when experimenting with chunk sizes. Command-line
options can override the three numeric values for one run without changing this file.
"""

# ``True`` and ``False`` are Python Boolean values. With this set to True, every
# Markdown heading starts a semantic section. Small sections remain whole;
# sections larger than TARGET_TOKENS are divided at safe Markdown block boundaries.
CHUNK_BY_HEADING = True

# Aim for children near this size. A token is a small piece of text used by an AI
# model; in English, 600 tokens is often roughly 400-500 words.
TARGET_TOKENS = 600

# Never intentionally create a retrieval child larger than this many model tokens.
MAX_TOKENS = 900

# Repeat up to this many tokens of complete blocks between adjacent child chunks.
# Overlap helps a search result retain context that falls near a split boundary.
OVERLAP_TOKENS = 75

# This tokenizer converts text into the same kind of units used by OpenAI-family
# models, making the size settings more meaningful than character counts.
TOKENIZER_ENCODING = "cl100k_base"

# Embedding settings
EMBEDDING_BATCH_SIZE = 32
DEFAULT_LOCAL_MODEL = "all-mpnet-base-v2"       # 768 dims, top quality on SBERT leaderboard
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"  # 1536 dims

# Output paths
JSONL_PATH = "output/react-doc-chunks.jsonl"
EMBED_CACHE_PATH = "output/embed_cache.db"
CHROMA_DB_DIR = "output/chroma_db"
CHROMA_COLLECTION = "react_docs"
QDRANT_DB_DIR = "output/qdrant_db"
QDRANT_COLLECTION = "react_docs"
