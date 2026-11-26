"""Извлечение текста из PDF: нормализация, удаление колонтитулов, переносов.

Страницы нумеруются по PDF (как требует ТЗ), нумерация начинается с 1.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pymupdf

from .manuals import Manual

PAGE_NUMBER_RE = re.compile(r"^\d{1,4}$")
NON_WORD_RE = re.compile(r"[^0-9a-zа-яё]+", re.I)
HYPHEN_BREAK_RE = re.compile(r"([а-яёa-z])-\s*\n\s*([а-яёa-z])", re.I)


def _norm_line(line: str) -> str:
    """Нормализация строки для подсчёта повторов (цифры → #)."""
    s = NON_WORD_RE.sub(" ", line.lower().replace("ё", "е")).strip()
    return re.sub(r"\d+", "#", s)


def detect_running_lines(pages: list[list[str]]) -> set[str]:
    """Колонтитулы: строки, которые повторяются на многих страницах сверху/снизу."""
    counter: Counter[str] = Counter()
    for lines in pages:
        edge = lines[:4] + lines[-4:]
        counter.update({_norm_line(x) for x in edge if x.strip()})
    threshold = max(5, int(0.15 * len(pages)))
    return {key for key, n in counter.items() if n >= threshold and len(key) > 3}


def clean_page(text: str, running: set[str]) -> str:
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        norm = _norm_line(line)
        if norm in running:
            continue
        if PAGE_NUMBER_RE.match(line):
            continue
        kept.append(line)
    joined = "\n".join(kept)
    joined = HYPHEN_BREAK_RE.sub(r"\1\2", joined)
    joined = joined.replace("­", "")
    joined = re.sub(r"\s*\n\s*", " ", joined)
    return re.sub(r"\s+", " ", joined).strip()


def load_pages(path: Path) -> list[list[str]]:
    doc = pymupdf.open(path)
    try:
        return [doc[i].get_text().splitlines() for i in range(doc.page_count)]
    finally:
        doc.close()


def extract_document(manual: Manual, manuals_dir: Path) -> list[dict]:
    path = manuals_dir / manual.file
    if not path.exists():
        raise FileNotFoundError(f"нет файла руководства: {path}")
    raw_pages = load_pages(path)
    running = detect_running_lines(raw_pages)
    pages: list[dict] = []
    for i, lines in enumerate(raw_pages, start=1):
        text = clean_page("\n".join(lines), running)
        pages.append(
            {
                "doc_id": manual.doc_id,
                "manual_ref": manual.manual_ref,
                "title": manual.title,
                "engines": list(manual.engines),
                "pdf_page": i,
                "text": text,
            }
        )
    return pages
