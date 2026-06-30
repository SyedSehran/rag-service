"""Embedding layer.

This environment has no outbound access to model-hosting endpoints (no API
key configured, no HF Hub egress), so the embedder implemented here is a
deterministic, dependency-free **hashing TF-IDF embedder**: each token is
hashed into one of `dim` buckets, weighted by log-scaled term frequency,
and the resulting vector is L2-normalized so cosine similarity == dot
product. This is the standard offline fallback for RAG prototypes (same
idea as `HashingVectorizer` in scikit-learn) and is good enough to validate
the pipeline end-to-end and to compute real retrieval metrics.

Swap-in point for production: replace `Embedder.embed()` with a call to
`text-embedding-3-small` (OpenAI, dim=1536) or `voyage-3-lite` (Voyage,
dim=512) -- both are listed in `app/config.py` as the intended production
default. Nothing else in the pipeline (store schema, retrieval, API)
changes, since the store treats embeddings as opaque float vectors of a
fixed declared dimensionality.
"""
from __future__ import annotations
import hashlib
import math
import re
import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _stable_hash(token: str) -> int:
    # Python's built-in hash() is randomized per-process (PYTHONHASHSEED);
    # we need a hash that is stable across restarts so re-ingest is reproducible.
    return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)


class Embedder:
    name = "hashing-tfidf-offline-v1"

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _tokenize(self, text: str) -> list[str]:
        return _TOKEN_RE.findall(text.lower())

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype="float32")
        tokens = self._tokenize(text)
        if not tokens:
            return vec
        counts: dict[int, int] = {}
        for tok in tokens:
            idx = _stable_hash(tok) % self.dim
            counts[idx] = counts.get(idx, 0) + 1
        for idx, c in counts.items():
            vec[idx] = 1.0 + math.log(c)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return np.stack([self.embed(t) for t in texts])
