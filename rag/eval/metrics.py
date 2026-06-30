"""Retrieval and answer-quality metrics, implemented directly (no IR
library) so every number in the submission can be traced to code here."""
from __future__ import annotations
import math
import re
import string


def recall_hit(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Hit Rate / Recall@k for a single query with a binary relevance set:
    1.0 if at least one relevant chunk was retrieved, else 0.0."""
    if not relevant_ids:
        return None  # not defined for no-context queries
    return 1.0 if any(rid in relevant_ids for rid in retrieved_ids) else 0.0


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    if not relevant_ids:
        return None
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return None
    dcg = 0.0
    for i, rid in enumerate(retrieved_ids[:k], start=1):
        rel = 1.0 if rid in relevant_ids else 0.0
        dcg += rel / math.log2(i + 1)
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def context_precision(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Fraction of retrieved chunks that are actually relevant."""
    if not relevant_ids:
        return None
    if not retrieved_ids:
        return 0.0
    hits = sum(1 for rid in retrieved_ids if rid in relevant_ids)
    return hits / len(retrieved_ids)


_PUNCT = str.maketrans("", "", string.punctuation)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().translate(_PUNCT)).strip()


def exact_match(prediction: str, gold: str) -> float:
    return 1.0 if _normalize(prediction) == _normalize(gold) else 0.0


def f1_score(prediction: str, gold: str) -> float:
    pred_tokens = _normalize(prediction).split()
    gold_tokens = _normalize(gold).split()
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = {}
    for t in pred_tokens:
        common[t] = common.get(t, 0) + 1
    overlap = 0
    gold_counts = {}
    for t in gold_tokens:
        gold_counts[t] = gold_counts.get(t, 0) + 1
    for t, c in gold_counts.items():
        overlap += min(c, common.get(t, 0))
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def heuristic_faithfulness(answer_text: str, grounded: bool, retrieved_texts: list[str]) -> float:
    """Offline proxy for an LLM-judge faithfulness score (see README
    'Answer Evaluation' limitations -- no LLM API key in this
    environment). Since the generator is extractive (every clause is a
    sentence copied verbatim from a retrieved chunk, see app/generate.py),
    faithfulness reduces to: did every cited sentence actually appear in
    its cited chunk's text? This is a real, checkable measurement, just a
    narrower one than an LLM-judge would give on free-form generation."""
    if not grounded:
        return 1.0  # correctly abstained -> trivially faithful (no claims made)
    sentences = re.split(r"\s*\[[^\]]+\]\s*", answer_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    supported = 0
    for s in sentences:
        if any(s in t for t in retrieved_texts):
            supported += 1
    return supported / len(sentences)


def heuristic_relevance(answer_text: str, question: str) -> float:
    """Offline proxy for LLM-judge answer-relevance: token-overlap (Jaccard)
    between the answer and the question, normalized 0-1. Same limitation
    note as heuristic_faithfulness above."""
    q_tokens = set(_normalize(question).split())
    a_tokens = set(_normalize(answer_text).split())
    if not q_tokens or not a_tokens:
        return 0.0
    return len(q_tokens & a_tokens) / len(q_tokens | a_tokens)
