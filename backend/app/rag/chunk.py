"""Нарезка страниц на чанки.

Правила:
* чанк никогда не пересекает границу страницы — иначе ссылка на страницу врёт;
* целевой размер ~700 символов, максимум ~1100, перекрытие в одно предложение;
* слишком длинные «предложения» (сплющенные таблицы) режутся по словам.
"""
from __future__ import annotations

import re

SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+(?=[«\"(А-ЯЁA-Z0-9])")
MIN_CHUNK = 90


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_RE.split(text) if p.strip()]
    result: list[str] = []
    for part in parts:
        if len(part) <= 600:
            result.append(part)
            continue
        # таблица/перечисление без точек: режем по словам
        words = part.split()
        buf: list[str] = []
        size = 0
        for w in words:
            if size + len(w) + 1 > 500 and buf:
                result.append(" ".join(buf))
                buf, size = [], 0
            buf.append(w)
            size += len(w) + 1
        if buf:
            result.append(" ".join(buf))
    return result


def chunk_page(page: dict, target: int = 700, max_len: int = 1100) -> list[dict]:
    text = page["text"]
    if not text:
        return []
    sentences = split_sentences(text)
    chunks: list[dict] = []
    buf: list[str] = []
    size = 0
    for sent in sentences:
        if buf and size + len(sent) + 1 > max_len:
            chunks.append(_make_chunk(page, buf))
            buf = buf[-1:] if len(buf[-1]) < target // 2 else []
            size = sum(len(x) + 1 for x in buf)
        buf.append(sent)
        size += len(sent) + 1
        if size >= target and len(buf) >= 2:
            chunks.append(_make_chunk(page, buf))
            buf = buf[-1:]
            size = sum(len(x) + 1 for x in buf)
    if buf:
        if chunks and sum(len(x) + 1 for x in buf) < MIN_CHUNK:
            chunks[-1]["text"] += " " + " ".join(buf)
        else:
            chunks.append(_make_chunk(page, buf))
    return [c for c in chunks if len(c["text"]) >= MIN_CHUNK]


def _make_chunk(page: dict, sentences: list[str]) -> dict:
    return {
        "doc_id": page["doc_id"],
        "manual_ref": page["manual_ref"],
        "title": page["title"],
        "engines": page["engines"],
        "pdf_page": page["pdf_page"],
        "text": " ".join(sentences).strip(),
    }
