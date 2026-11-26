"""Сборка поискового индекса из PDF руководств.

Запуск:  python backend/scripts/ingest.py
Пишет:   data/index/pages.jsonl, chunks.jsonl, bm25.pkl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import INDEX_DIR, MANUALS_DIR  # noqa: E402
from app.rag.chunk import chunk_page  # noqa: E402
from app.rag.extract import extract_document  # noqa: E402
from app.rag.index import BM25Index  # noqa: E402
from app.rag.manuals import MANUALS  # noqa: E402


def main() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    pages_path = INDEX_DIR / "pages.jsonl"
    chunks_path = INDEX_DIR / "chunks.jsonl"
    all_chunks: list[dict] = []

    with pages_path.open("w", encoding="utf-8") as pages_f, chunks_path.open(
        "w", encoding="utf-8"
    ) as chunks_f:
        for manual in MANUALS:
            pages = extract_document(manual, MANUALS_DIR)
            doc_chunks: list[dict] = []
            for page in pages:
                pages_f.write(json.dumps(page, ensure_ascii=False) + "\n")
                for chunk in chunk_page(page):
                    chunk["chunk_id"] = f"{manual.doc_id}:p{page['pdf_page']}:{len(doc_chunks)}"
                    doc_chunks.append(chunk)
            for chunk in doc_chunks:
                chunks_f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            all_chunks.extend(doc_chunks)
            empty = sum(1 for p in pages if len(p["text"]) < 30)
            print(
                f"{manual.doc_id:12} pages={len(pages):4} chunks={len(doc_chunks):5} "
                f"empty_pages={empty}"
            )

    BM25Index(all_chunks).save(INDEX_DIR / "bm25.pkl")
    print(f"\nВсего чанков: {len(all_chunks)}; индекс: {INDEX_DIR}")


if __name__ == "__main__":
    main()
