"""Поиск по руководствам: фильтр по двигателю и корректность ссылок."""
from __future__ import annotations

import pytest

from app.config import INDEX_DIR
from app.rag import tools

pytestmark = pytest.mark.skipif(
    not (INDEX_DIR / "bm25.pkl").exists(),
    reason="индекс не собран: python backend/scripts/ingest.py",
)

ENGINES = ["ЯМЗ-236М2", "ЯМЗ-536", "ЗМЗ-5234.10", "ЗМЗ-40904.10"]
JUNK = "турбина интеркулер форсунка Common Rail EGR DPF AdBlue"


def test_engine_filter_returns_only_own_manuals():
    for engine in ENGINES:
        allowed = tools.allowed_manuals(engine)
        assert allowed, engine
        for hit in tools.search(JUNK, engine, top_k=8):
            assert hit["manual"] in allowed, (engine, hit["manual"])


def test_results_carry_manual_and_pdf_page():
    hits = tools.search("момент затяжки головки цилиндров", "ЯМЗ-236М2", top_k=6)
    assert hits
    for hit in hits:
        assert hit["manual"]
        assert hit["pdf_page"] >= 1
        assert hit["text"].strip()
        assert hit["score"] > 0


def test_unknown_engine_returns_nothing():
    assert tools.allowed_manuals("ДВС-2099") == set()
    assert tools.search("давление масла", "ДВС-2099", top_k=6) == []


def test_pages_are_bounded_by_document():
    manual = "236.01.01 РК"
    assert tools.manual_page_count(manual) > 100
    assert tools.page_text(manual, 20)
    assert tools.page_text(manual, 10**6) is None


def test_search_is_deterministic():
    first = tools.search("зазоры клапанов", "ЗМЗ-5234.10", top_k=5)
    second = tools.search("зазоры клапанов", "ЗМЗ-5234.10", top_k=5)
    assert [(h["manual"], h["pdf_page"]) for h in first] == [
        (h["manual"], h["pdf_page"]) for h in second
    ]
