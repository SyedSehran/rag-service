import os

CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "180"))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "40"))
EMBED_DIM = int(os.environ.get("RAG_EMBED_DIM", "384"))
STORE_PATH = os.environ.get("RAG_STORE_PATH", "./data/store")
DEFAULT_K = int(os.environ.get("RAG_DEFAULT_K", "5"))
NO_CONTEXT_THRESHOLD = float(os.environ.get("RAG_NO_CONTEXT_THRESHOLD", "0.12"))
# Below this top-1 cosine score, the retriever has not found anything
# meaningfully related to the query, so generation refuses rather than
# hallucinating an answer from weakly-related chunks.

# Production swap point (not used by the offline embedder/generator below,
# kept here so the config story is real even though no key is set in this
# environment):
LLM_API_KEY = os.environ.get("RAG_LLM_API_KEY", "")
LLM_MODEL = os.environ.get("RAG_LLM_MODEL", "")
