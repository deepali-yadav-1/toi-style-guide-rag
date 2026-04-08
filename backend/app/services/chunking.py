from __future__ import annotations

import re


SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+")


def split_into_chunks(
    text: str,
    *,
    target_size: int = 1100,
    overlap_size: int = 180,
) -> list[str]:
    sentences = [segment.strip() for segment in SENTENCE_BOUNDARY_PATTERN.split(text) if segment.strip()]
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)
        if current and current_length + sentence_length > target_size:
            chunk_text = " ".join(current).strip()
            if chunk_text:
                chunks.append(chunk_text)

            overlap_sentences: list[str] = []
            overlap_length = 0
            for existing in reversed(current):
                overlap_sentences.insert(0, existing)
                overlap_length += len(existing)
                if overlap_length >= overlap_size:
                    break

            current = overlap_sentences.copy()
            current_length = sum(len(item) for item in current)

        current.append(sentence)
        current_length += sentence_length

    trailing = " ".join(current).strip()
    if trailing:
        chunks.append(trailing)

    return chunks
