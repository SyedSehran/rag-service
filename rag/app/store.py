"""Vector store: a small pure-NumPy flat index (cosine via dot product on
normalized vectors) + a parallel SQLite table for metadata, filtering, and
the chunk_id -> row mapping that makes re-ingest idempotent.

Why not FAISS: FAISS ships as a compiled wheel and its PyPI release cadence
lags new CPython releases by months, so it has no prebuilt wheel for very
new Python versions (e.g. 3.14 at the time of writing) and pip falls back
to a source build that usually fails without local build tooling. A flat
index over a few thousand vectors is just `(index @ query)` plus an
argsort, so reimplementing it in ~40 lines of NumPy removes a fragile
dependency entirely, at the cost of true large-scale ANN search -- a
trade-off discussed in the README (this corpus has 10 vectors; the
brute-force approach is exact and fast at this scale, and the swap-in
point for a real ANN library at 100K+ vectors is noted there too).

Why FAISS/an ANN index would still matter at scale: this assignment's own
brief is about cost behavior from ~100K to 10M vectors -- a brute-force
NumPy scan is O(n) per query, which is fine for a demo corpus and is
exactly why the cost-comparison numbers explicitly assume FAISS/an ANN
index in production (see eval/cost_comparison.py docstring) even though
this particular run uses the NumPy fallback for portability.
"""
from __future__ import annotations
import os
import sqlite3
import threading
import numpy as np


class VectorStore:
    def __init__(self, path: str, dim: int):
        self.path = path
        self.dim = dim
        os.makedirs(path, exist_ok=True)
        self.vectors_path = os.path.join(path, "vectors.npy")
        self.db_path = os.path.join(path, "meta.sqlite")
        self._lock = threading.Lock()

        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                position INTEGER NOT NULL,
                heading TEXT,
                text TEXT NOT NULL
            )
        """)
        self.db.commit()

        if os.path.exists(self.vectors_path):
            self._vectors = np.load(self.vectors_path)
            if self._vectors.shape[0] == 0:
                self._vectors = np.zeros((0, dim), dtype="float32")
        else:
            self._vectors = np.zeros((0, dim), dtype="float32")

    def _save(self):
        np.save(self.vectors_path, self._vectors)

    def existing_chunk_ids(self) -> set[str]:
        cur = self.db.execute("SELECT chunk_id FROM chunks")
        return {row[0] for row in cur.fetchall()}

    def upsert(self, chunk_id: str, source: str, position: int, heading: str | None,
               text: str, vector: np.ndarray) -> bool:
        """Insert a chunk if its chunk_id hasn't been seen before.

        Returns True if a new vector was added, False if it was a no-op
        because the chunk already existed (this is the idempotency
        guarantee: chunk_id is a hash of source+position+text, so
        re-running ingest on an unchanged corpus adds zero new vectors).
        """
        with self._lock:
            cur = self.db.execute("SELECT 1 FROM chunks WHERE chunk_id = ?", (chunk_id,))
            if cur.fetchone() is not None:
                return False
            self.db.execute(
                "INSERT INTO chunks (chunk_id, source, position, heading, text) VALUES (?,?,?,?,?)",
                (chunk_id, source, position, heading, text),
            )
            self.db.commit()
            self._vectors = np.vstack([self._vectors, vector.reshape(1, -1).astype("float32")])
            self._save()
            return True

    def count(self) -> int:
        return self._vectors.shape[0]

    def search(self, query_vector: np.ndarray, k: int, source_filter: str | None = None):
        """Top-k search, optionally filtered by `source` metadata.

        Brute-force cosine similarity (vectors are L2-normalized at embed
        time, so dot product == cosine). When a filter is given we
        over-fetch (k * over-fetch-factor, capped by index size) and then
        filter in SQLite -- fine at this corpus size; the README discusses
        the alternative (per-source sub-indices) for when the filtered
        class is rare relative to the corpus.
        """
        n = self._vectors.shape[0]
        if n == 0:
            return []
        fetch_k = min(n, k * 8 if source_filter else k)
        scores = self._vectors @ query_vector.astype("float32")
        if fetch_k < n:
            top_idx = np.argpartition(-scores, fetch_k - 1)[:fetch_k]
        else:
            top_idx = np.arange(n)
        top_idx = top_idx[np.argsort(-scores[top_idx])]

        results = []
        for row_id in top_idx:
            score = float(scores[row_id])
            # numpy row index == sqlite AUTOINCREMENT - 1 (insertion order)
            cur = self.db.execute(
                "SELECT chunk_id, source, position, heading, text FROM chunks WHERE row_id = ?",
                (int(row_id) + 1,),
            )
            row = cur.fetchone()
            if row is None:
                continue
            chunk_id, source, position, heading, text = row
            if source_filter and source != source_filter:
                continue
            results.append({
                "chunk_id": chunk_id,
                "source": source,
                "position": position,
                "heading": heading,
                "text": text,
                "score": score,
            })
            if len(results) >= k:
                break
        return results
