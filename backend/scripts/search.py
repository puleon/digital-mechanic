"""Поиск по руководствам из командной строки.

Пример:
  python backend/scripts/search.py "момент затяжки крышек коренных подшипников" --engine ЯМЗ-236М2
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import INDEX_DIR  # noqa: E402
from app.rag.index import BM25Index  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--engine", default=None)
    parser.add_argument("--top", type=int, default=6)
    args = parser.parse_args()

    index = BM25Index.load(INDEX_DIR / "bm25.pkl")
    engines = [args.engine] if args.engine else None
    for i, hit in enumerate(index.search(args.query, engines=engines, top_k=args.top), 1):
        print(f"\n[{i}] score={hit['score']}  {hit['manual_ref']}  стр. {hit['pdf_page']}")
        print(f"    {hit['text'][:500]}")


if __name__ == "__main__":
    main()
