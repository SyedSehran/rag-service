# Aster RAG Service

A small QA service over a 5-document corpus (a fictional cloud-storage product's docs), backed by FAISS, with a real measured evaluation harness across retrieval, answer quality, and cost.

## Why FAISS-style flat indexing (not the FAISS library itself)

The brief is about a lightly-queried, large-vector-count index where a pod-based managed DB's always-on billing dominates cost. The retrieval layer here implements a FAISS-style flat index (cosine similarity via dot product on normalized vectors) **in pure NumPy** rather than depending on the `faiss-cpu` package: FAISS ships as a compiled wheel and its PyPI release cadence lags new CPython releases, so it commonly has no prebuilt wheel for a brand-new Python version and pip falls back to a source build that fails without local build tools. At this corpus size (10 vectors) a brute-force NumPy scan is exact and effectively free; `app/store.py`'s docstring documents the swap-in point for a real ANN library (FAISS, an `IndexIVF`/HNSW variant, etc.) once the corpus is large enough that O(n)-per-query brute force stops being fast enough — exactly the 100K–10M-vector regime the cost-comparison table targets. Either way, the cost model (zero always-on infra, file-based persistence, no idle pod) is the same; only the in-memory search algorithm differs.

## Important: offline-mode disclosure

This environment had no LLM/embedding API key configured. Rather than fake the numbers, two components are implemented as **honest offline substitutes**, clearly marked in code (`app/embeddings.py`, `app/generate.py`):

- **Embeddings**: a deterministic hashing TF-IDF embedder (384-dim), not a neural embedding model. Swap-in point for `text-embedding-3-small` or `voyage-3-lite` is documented in `app/config.py` / `app/embeddings.py`.
- **Generation**: an extractive answerer — it selects and cites the most query-relevant sentences from retrieved chunks verbatim, rather than calling an LLM. Swap-in point is documented in `app/generate.py`.
- **Answer-quality judge**: faithfulness/relevance are computed with offline heuristic proxies (`eval/metrics.py`), not an LLM-as-judge, since there is no model to call. This is the single biggest fidelity gap versus the assignment brief and is called out again in the Discussion section.

Every metric reported below was actually computed by running this code, not estimated.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit if you want non-default chunk size / k / etc.
```

## Ingest

```bash
python -m app.ingest --corpus ./corpus
# re-run on the same corpus -> "new_vectors_added=0" (idempotent)
```

## Run the service

```bash
uvicorn app.api:app --reload --port 8000
curl -X POST localhost:8000/query -H 'Content-Type: application/json' \
  -d '{"query": "What encryption does Aster use at rest?", "k": 5}'
```

## Run the evaluation harness

```bash
python -m eval.run_eval --k 5      # writes eval/results.json and eval/results.md
python -m eval.cost_comparison     # prints the cost table
```

## Config (env vars, no secrets committed)

`RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_EMBED_DIM`, `RAG_STORE_PATH`, `RAG_DEFAULT_K`, `RAG_NO_CONTEXT_THRESHOLD`, `RAG_LLM_API_KEY` (unused in offline mode), `RAG_LLM_MODEL` (unused in offline mode).

## Discussion

**Chunking**: 180 words / 40-word overlap, picked after eyeballing the corpus — most source sections are 80–250 words, so this usually keeps one chunk inside one logical section. At smaller sizes (~60 words) sections got split mid-sentence and the extractive answerer started citing fragments; at larger sizes (~400 words) the metadata-light chunks started mixing two unrelated headings in one vector, lowering context precision.

**No relevant context handling**: the generator refuses to answer if the top retrieved score is below `RAG_NO_CONTEXT_THRESHOLD` (0.12) or if no sentence in the retrieved chunks shares any token with the query. The eval run exposed a real weakness here: the off-topic gold question ("capital of France") still scored 0.33 against an unrelated chunk, well above threshold, because the hashing embedder has no real semantics — token-hash collisions in a 384-dim space produce nonzero cosine similarity even for unrelated text. `no_context_handling_accuracy` in the results is 0/1 on this question, which is an honest, reproducible failure, not a hidden one. The fix is the embedding swap-in (a real neural embedder would push unrelated text far lower), not a different threshold.

**Idempotent re-ingest**: `chunk_id = sha256(source, position, chunk_text)`. The store's `upsert()` checks for that id in SQLite before adding anything to the FAISS index, so re-running ingest on an unchanged corpus is a guaranteed no-op (see `eval` output above: second ingest run added 0 vectors). If a source file's content changes, its chunk boundaries shift, hashes change, and new vectors are added alongside (not replacing) the old ones — stale-chunk garbage collection on file change is a known gap, noted as future work.

**Retrieval vs generation — which is the weak link**: retrieval. `context_precision` came out at 0.14 — most retrieved chunks at k=5 are not actually relevant, because the corpus only has 1-2 truly relevant chunks per question but k=5 always returns 5. Hit-rate (0.71) and MRR (0.51) show the *right* chunk is usually found, just buried among irrelevant ones, which a smaller k or a real embedding model (sharper semantic separation) would both improve. Faithfulness was a clean 1.0 by construction (the generator can only emit sentences copied from retrieved text), so generation was never the source of factual errors in this run — but that's partly because extractive generation can't paraphrase or synthesize, which is its own quality ceiling, discussed below.

**When to switch back to a managed DB**: once query volume gets high enough that read latency / availability SLAs matter more than idle-pod cost, or once the corpus needs frequent metadata-filtered writes at high QPS — FAISS's filter-by-overfetch approach (`app/store.py`) degrades as the filtered subset shrinks relative to the corpus. At the scale tested here (10 docs, 10 chunks) this is a non-issue; at 10M vectors with a rare filter value it would mean scanning a large multiple of k before finding enough filtered hits.

**Known fidelity gap vs. the brief**: with a real LLM in the loop, faithfulness/relevance would be judged by an actual model reading the answer against the source, not by a sentence-membership heuristic, and generation could synthesize across chunks instead of only concatenating sentences. The architecture is built so that swapping in a real embedding model and a real LLM call (config keys already exist, see `.env.example`) doesn't change anything else in the pipeline — store schema, retrieval, the no-context guard, and the eval harness's metric *definitions* (just not their offline proxy implementations for faithfulness/relevance) all stay the same.
