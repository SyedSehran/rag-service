"""Ingest a folder of .md/.txt/.html files into the vector store.

Usage:
    python -m app.ingest --corpus ./corpus

Re-running this on an unchanged corpus adds zero new vectors (idempotent),
because chunk_id = sha256(source, position, chunk_text) and the store
skips any chunk_id already present.
"""
from __future__ import annotations
import argparse
import glob
import os
import re
import time

from app import config
from app.chunking import chunk_document
from app.embeddings import Embedder
from app.store import VectorStore


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_text(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    if filepath.endswith(".html") or filepath.endswith(".htm"):
        return _strip_html(raw)
    return raw


def ingest(corpus_dir: str, store: VectorStore, embedder: Embedder) -> dict:
    files = sorted(
        glob.glob(os.path.join(corpus_dir, "**", "*.md"), recursive=True)
        + glob.glob(os.path.join(corpus_dir, "**", "*.txt"), recursive=True)
        + glob.glob(os.path.join(corpus_dir, "**", "*.html"), recursive=True)
    )
    t0 = time.time()
    total_chunks = 0
    new_vectors = 0
    for fp in files:
        text = load_text(fp)
        source = os.path.basename(fp)
        chunks = chunk_document(source, text, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        total_chunks += len(chunks)
        for ch in chunks:
            vec = embedder.embed(ch.text)
            added = store.upsert(ch.chunk_id, ch.source, ch.position, ch.heading, ch.text, vec)
            if added:
                new_vectors += 1
    elapsed = time.time() - t0
    return {
        "files_scanned": len(files),
        "chunks_seen": total_chunks,
        "new_vectors_added": new_vectors,
        "store_total_vectors": store.count(),
        "elapsed_sec": round(elapsed, 3),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--store", default=config.STORE_PATH)
    args = parser.parse_args()

    embedder = Embedder(dim=config.EMBED_DIM)
    store = VectorStore(args.store, dim=config.EMBED_DIM)
    result = ingest(args.corpus, store, embedder)
    print(f"[ingest] embed_model={embedder.name} dim={embedder.dim} "
          f"chunk_size={config.CHUNK_SIZE} overlap={config.CHUNK_OVERLAP}")
    print(f"[ingest] files_scanned={result['files_scanned']} "
          f"chunks_seen={result['chunks_seen']} "
          f"new_vectors_added={result['new_vectors_added']} "
          f"store_total_vectors={result['store_total_vectors']} "
          f"elapsed_sec={result['elapsed_sec']}")
