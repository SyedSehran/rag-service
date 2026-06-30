from __future__ import annotations
import json
import logging
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import config
from app.embeddings import Embedder
from app.generate import Generator
from app.store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("rag")

app = FastAPI(title="Aster RAG Service")

embedder = Embedder(dim=config.EMBED_DIM)
store = VectorStore(config.STORE_PATH, dim=config.EMBED_DIM)
generator = Generator(no_context_threshold=config.NO_CONTEXT_THRESHOLD)


class QueryRequest(BaseModel):
    query: str
    k: int | None = None
    source_filter: str | None = None


class QueryResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[dict]
    retrieved_chunks: list[dict]
    latency_ms: float
    chunk_count: int
    token_usage_estimate: int


@app.get("/health")
def health():
    return {"status": "ok", "vectors_indexed": store.count(), "embed_model": embedder.name}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(400, "query must not be empty")
    k = req.k or config.DEFAULT_K
    t0 = time.perf_counter()

    qvec = embedder.embed(req.query)
    retrieved = store.search(qvec, k=k, source_filter=req.source_filter)
    ans = generator.answer(req.query, retrieved)

    latency_ms = (time.perf_counter() - t0) * 1000

    log_record = {
        "event": "query",
        "query": req.query,
        "k": k,
        "source_filter": req.source_filter,
        "chunk_count": len(retrieved),
        "grounded": ans.grounded,
        "token_usage_estimate": ans.token_usage_estimate,
        "latency_ms": round(latency_ms, 2),
    }
    logger.info(json.dumps(log_record))

    return QueryResponse(
        answer=ans.text,
        grounded=ans.grounded,
        citations=ans.citations,
        retrieved_chunks=[{"source": r["source"], "position": r["position"], "score": round(r["score"], 4)} for r in retrieved],
        latency_ms=round(latency_ms, 2),
        chunk_count=len(retrieved),
        token_usage_estimate=ans.token_usage_estimate,
    )
