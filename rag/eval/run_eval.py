"""Runs the fixed gold question set through the live pipeline and
produces eval/results.json + eval/results.md with all three metric
layers (retrieval, answer, latency). Cost comparison is a separate,
static calculation (see eval/cost_comparison.py) since it does not
depend on running queries.

Usage: python -m eval.run_eval --k 5
"""
from __future__ import annotations
import argparse
import json
import statistics
import time

from app import config
from app.embeddings import Embedder
from app.generate import Generator
from app.store import VectorStore
from eval import metrics as M


def run(k: int):
    with open("eval/gold_questions.json") as f:
        gold = json.load(f)

    embedder = Embedder(dim=config.EMBED_DIM)
    store = VectorStore(config.STORE_PATH, dim=config.EMBED_DIM)
    generator = Generator(no_context_threshold=config.NO_CONTEXT_THRESHOLD)

    per_query = []
    latencies = []

    for item in gold:
        relevant_ids = set(item["relevant_chunk_ids"])
        t0 = time.perf_counter()
        qvec = embedder.embed(item["question"])
        retrieved = store.search(qvec, k=k)
        ans = generator.answer(item["question"], retrieved)
        latency_ms = (time.perf_counter() - t0) * 1000
        latencies.append(latency_ms)

        retrieved_ids = [r["chunk_id"] for r in retrieved]
        retrieved_texts = [r["text"] for r in retrieved]

        row = {
            "id": item["id"],
            "question": item["question"],
            "k": k,
            "retrieved_ids": retrieved_ids,
            "relevant_ids": list(relevant_ids),
            "hit": M.recall_hit(retrieved_ids, relevant_ids),
            "rr": M.reciprocal_rank(retrieved_ids, relevant_ids),
            "ndcg": M.ndcg_at_k(retrieved_ids, relevant_ids, k),
            "context_precision": M.context_precision(retrieved_ids, relevant_ids),
            "answer": ans.text,
            "grounded": ans.grounded,
            "expected_no_context": item["gold_answer"] == "NO_RELEVANT_CONTEXT",
            "faithfulness": M.heuristic_faithfulness(ans.text, ans.grounded, retrieved_texts),
            "relevance": M.heuristic_relevance(ans.text, item["question"]),
            "em": None if item["gold_answer"] == "NO_RELEVANT_CONTEXT" else M.exact_match(ans.text, item["gold_answer"]),
            "f1": None if item["gold_answer"] == "NO_RELEVANT_CONTEXT" else M.f1_score(ans.text, item["gold_answer"]),
            "latency_ms": round(latency_ms, 3),
            "token_usage_estimate": ans.token_usage_estimate,
        }
        per_query.append(row)

    def avg(key):
        vals = [r[key] for r in per_query if r[key] is not None]
        return sum(vals) / len(vals) if vals else None

    latencies_sorted = sorted(latencies)
    def pct(p):
        idx = min(len(latencies_sorted) - 1, int(round(p * (len(latencies_sorted) - 1))))
        return latencies_sorted[idx]

    # no-context correctness: for the one query with no relevant chunks,
    # did the generator correctly abstain?
    no_context_rows = [r for r in per_query if r["expected_no_context"]]
    no_context_correct = sum(1 for r in no_context_rows if not r["grounded"]) / len(no_context_rows) if no_context_rows else None

    summary = {
        "k": k,
        "n_questions": len(gold),
        "embed_model": embedder.name,
        "embed_dim": embedder.dim,
        "retrieval": {
            "recall_at_k_hit_rate": avg("hit"),
            "mrr": avg("rr"),
            "ndcg_at_k": avg("ndcg"),
            "context_precision": avg("context_precision"),
        },
        "answer": {
            "faithfulness_mean": avg("faithfulness"),
            "relevance_mean": avg("relevance"),
            "em_mean": avg("em"),
            "f1_mean": avg("f1"),
            "no_context_handling_accuracy": no_context_correct,
        },
        "latency_ms": {
            "p50": pct(0.50),
            "p95": pct(0.95),
            "mean": statistics.mean(latencies),
        },
    }

    with open("eval/results.json", "w") as f:
        json.dump({"summary": summary, "per_query": per_query}, f, indent=2)

    with open("eval/results.md", "w") as f:
        f.write("# Evaluation Results\n\n")
        f.write(f"k={k}, n={len(gold)} questions, embed_model={embedder.name} (dim={embedder.dim})\n\n")
        f.write("## Retrieval\n\n")
        for key, val in summary["retrieval"].items():
            f.write(f"- {key}: {val:.3f}\n" if val is not None else f"- {key}: N/A\n")
        f.write("\n## Answer\n\n")
        for key, val in summary["answer"].items():
            f.write(f"- {key}: {val:.3f}\n" if val is not None else f"- {key}: N/A\n")
        f.write("\n## Latency (ms)\n\n")
        for key, val in summary["latency_ms"].items():
            f.write(f"- {key}: {val:.3f}\n")
        f.write("\n## Per-query detail\n\n")
        for r in per_query:
            f.write(f"### {r['id']}: {r['question']}\n")
            f.write(f"- hit={r['hit']} rr={r['rr']} ndcg={r['ndcg']} ctx_precision={r['context_precision']}\n")
            f.write(f"- faithfulness={r['faithfulness']} relevance={r['relevance']} em={r['em']} f1={r['f1']}\n")
            f.write(f"- grounded={r['grounded']} latency_ms={r['latency_ms']} tokens={r['token_usage_estimate']}\n")
            f.write(f"- answer: {r['answer']}\n\n")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=config.DEFAULT_K)
    args = parser.parse_args()
    run(args.k)
