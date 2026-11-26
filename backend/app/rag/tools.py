"""Поиск по руководствам как инструмент агента."""
from __future__ import annotations

import json
from functools import lru_cache

from ..config import INDEX_DIR
from .index import BM25Index
from .manuals import MANUALS


@lru_cache(maxsize=1)
def _index() -> BM25Index:
    return BM25Index.load(INDEX_DIR / "bm25.pkl")


@lru_cache(maxsize=1)
def _page_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    with (INDEX_DIR / "pages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            page = json.loads(line)
            counts[page["doc_id"]] = max(counts.get(page["doc_id"], 0), page["pdf_page"])
    return counts


def allowed_manuals(engine_model: str) -> set[str]:
    return {m.manual_ref for m in MANUALS if engine_model in m.engines}


def manual_page_count(manual_ref: str) -> int:
    for m in MANUALS:
        if m.manual_ref == manual_ref:
            return _page_counts().get(m.doc_id, 0)
    return 0


def search(query: str, engine_model: str, top_k: int = 6) -> list[dict]:
    hits = _index().search(query, engines=[engine_model], top_k=top_k)
    return [
        {
            "manual": h["manual_ref"],
            "pdf_page": h["pdf_page"],
            "doc_title": h["title"],
            "text": h["text"],
            "score": h["score"],
        }
        for h in hits
    ]


def page_text(manual_ref: str, pdf_page: int) -> str | None:
    for m in MANUALS:
        if m.manual_ref != manual_ref:
            continue
        with (INDEX_DIR / "pages.jsonl").open(encoding="utf-8") as f:
            for line in f:
                page = json.loads(line)
                if page["doc_id"] == m.doc_id and page["pdf_page"] == pdf_page:
                    return page["text"]
    return None
