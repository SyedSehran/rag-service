"""Chunking: splits raw document text into overlapping word-windows.

Defaults: chunk_size=180 words, overlap=40 words. These were picked after
manual inspection of the corpus (see README "Design Decisions") -- most
sections in the source docs run 80-250 words, so 180/40 keeps each chunk
inside one logical section most of the time while still giving the next
chunk enough shared context to avoid hard truth-cutoffs at the boundary.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Chunk:
    chunk_id: str          # stable hash of (source, position, text) -> used for idempotent re-ingest
    source: str
    position: int
    text: str
    heading: str | None


def _stable_id(source: str, position: int, text: str) -> str:
    h = hashlib.sha256(f"{source}|{position}|{text}".encode("utf-8")).hexdigest()
    return h[:24]


def _current_heading(lines_seen: list[str]) -> str | None:
    for line in reversed(lines_seen):
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return None


def chunk_document(source: str, text: str, chunk_size: int = 180, overlap: int = 40) -> list[Chunk]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    lines = text.splitlines()
    words: list[str] = []
    word_to_heading: list[str | None] = []
    seen_headings: list[str] = []
    for line in lines:
        if line.startswith("#"):
            seen_headings.append(line)
        line_words = line.split()
        words.extend(line_words)
        word_to_heading.extend([_current_heading(seen_headings)] * len(line_words))

    chunks: list[Chunk] = []
    step = chunk_size - overlap
    position = 0
    i = 0
    while i < len(words):
        window = words[i:i + chunk_size]
        if not window:
            break
        chunk_text = " ".join(window)
        heading = word_to_heading[i] if i < len(word_to_heading) else None
        chunks.append(Chunk(
            chunk_id=_stable_id(source, position, chunk_text),
            source=source,
            position=position,
            text=chunk_text,
            heading=heading,
        ))
        position += 1
        i += step
        if i + chunk_size >= len(words) and i < len(words):
            # let the final window run to the end instead of producing a tiny tail chunk
            window = words[i:]
            if window:
                chunk_text = " ".join(window)
                heading = word_to_heading[i] if i < len(word_to_heading) else None
                chunks.append(Chunk(
                    chunk_id=_stable_id(source, position, chunk_text),
                    source=source,
                    position=position,
                    text=chunk_text,
                    heading=heading,
                ))
            break
    return chunks
