"""Оценка поиска по руководствам на контрольном наборе вопросов.

Запуск:
  python backend/scripts/eval_rag.py            # hit@1, hit@3, MRR
  python backend/scripts/eval_rag.py --top 8
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import ROOT  # noqa: E402
from app.rag import tools  # noqa: E402

QUESTIONS = ROOT / "backend" / "eval" / "questions.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=6)
    args = parser.parse_args()

    questions = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line]
    hit1 = hit3 = 0
    reciprocal = 0.0
    failures: list[str] = []

    for item in questions:
        expected = {(e["manual"], e["page"]) for e in item["expected"]}
        hits = tools.search(item["question"], item["engine"], top_k=args.top)
        pages = [(h["manual"], h["pdf_page"]) for h in hits]
        rank = next((i + 1 for i, p in enumerate(pages) if p in expected), None)
        if rank == 1:
            hit1 += 1
        if rank and rank <= 3:
            hit3 += 1
        if rank:
            reciprocal += 1 / rank
        else:
            failures.append(item["id"])
        mark = f"@{rank}" if rank else "MISS"
        top = ", ".join(f"{m} p{p}" for m, p in pages[:3])
        print(f"{item['id']:<24} {mark:<6} top3: {top}")

    total = len(questions)
    print()
    print(f"Вопросов: {total}")
    print(f"hit@1: {hit1 / total:.0%}   hit@3: {hit3 / total:.0%}   MRR: {reciprocal / total:.2f}")
    if failures:
        print("Промахи:", ", ".join(failures))


if __name__ == "__main__":
    main()
