"""Answer generation.

No LLM API key is configured in this environment (by design for this
submission -- see README), so this is an **extractive** grounded answerer:
it scores every sentence in the retrieved chunks against the query by
token overlap, returns the best-supported sentences verbatim, and tags
each with the chunk it came from. This keeps the "grounded answer that
cites the chunks it used" requirement honestly satisfiable without an LLM
in the loop, and isolates the retrieval-quality measurement from
generation-quality measurement (Problem 1 README discusses why this
matters for "was retrieval or generation the weak link").

Swap-in point for production: replace `Generator.answer()`'s body with a
call to an LLM (`config.LLM_MODEL` / `config.LLM_API_KEY`) using a prompt
that includes the retrieved chunks and asks for an answer plus citations;
the no-context guard and citation-formatting logic stay the same.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


@dataclass
class Answer:
    text: str
    citations: list[dict]
    grounded: bool
    token_usage_estimate: int = 0


class Generator:
    name = "extractive-offline-v1"

    def __init__(self, no_context_threshold: float = 0.12, max_sentences: int = 3):
        self.no_context_threshold = no_context_threshold
        self.max_sentences = max_sentences

    def answer(self, query: str, retrieved: list[dict]) -> Answer:
        if not retrieved or retrieved[0]["score"] < self.no_context_threshold:
            return Answer(
                text="I don't have enough relevant context in the indexed corpus to answer that confidently.",
                citations=[],
                grounded=False,
                token_usage_estimate=_estimate_tokens(query) + 20,
            )

        query_tokens = _tokenize(query)
        scored_sentences = []
        for chunk in retrieved:
            for sent in _SENT_SPLIT.split(chunk["text"]):
                sent = sent.strip()
                if len(sent) < 15:
                    continue
                sent_tokens = _tokenize(sent)
                overlap = len(query_tokens & sent_tokens)
                if overlap == 0:
                    continue
                jaccard = overlap / max(1, len(query_tokens | sent_tokens))
                scored_sentences.append((jaccard, sent, chunk))

        if not scored_sentences:
            return Answer(
                text="I don't have enough relevant context in the indexed corpus to answer that confidently.",
                citations=[],
                grounded=False,
                token_usage_estimate=_estimate_tokens(query) + 20,
            )

        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        top = scored_sentences[: self.max_sentences]

        seen_chunks = {}
        answer_parts = []
        for _, sent, chunk in top:
            tag = f"[{chunk['source']}#{chunk['position']}]"
            answer_parts.append(f"{sent} {tag}")
            seen_chunks[chunk["chunk_id"]] = chunk

        text = " ".join(answer_parts)
        citations = [
            {"chunk_id": c["chunk_id"], "source": c["source"], "position": c["position"]}
            for c in seen_chunks.values()
        ]
        usage = _estimate_tokens(query) + sum(_estimate_tokens(c["text"]) for c in retrieved) + _estimate_tokens(text)
        return Answer(text=text, citations=citations, grounded=True, token_usage_estimate=usage)


def _estimate_tokens(text: str) -> int:
    # ~0.75 words/token is the usual rule of thumb for English text with
    # GPT/Claude-style BPE tokenizers; used here only for logging since
    # there is no real tokenizer call in the offline path.
    words = len(text.split())
    return max(1, round(words / 0.75))
