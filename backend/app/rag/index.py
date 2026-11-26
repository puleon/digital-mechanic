"""Лексический поиск по руководствам (BM25) с фильтром по модели двигателя."""
from __future__ import annotations

import pickle
import re
from collections import defaultdict
from pathlib import Path

import snowballstemmer
from rank_bm25 import BM25Okapi

_stemmer = snowballstemmer.stemmer("russian")
WORD_RE = re.compile(r"[0-9a-zа-яё]+", re.I)


def tokenize(text: str) -> list[str]:
    words = WORD_RE.findall(text.lower().replace("ё", "е"))
    return [_stemmer.stemWord(w) for w in words]


class BM25Index:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self._tokens = [tokenize(c["text"]) for c in chunks]
        self._bm25 = BM25Okapi(self._tokens)

    def search(
        self,
        query: str,
        engines: list[str] | None = None,
        top_k: int = 8,
        max_per_page: int = 2,
    ) -> list[dict]:
        """Возвращает чанки с полем score, только по документам нужного двигателя."""
        scores = self._bm25.get_scores(tokenize(query))
        allowed = set(engines) if engines else None
        per_page: dict[tuple[str, int], int] = defaultdict(int)
        results: list[dict] = []
        for i in sorted(range(len(scores)), key=lambda j: scores[j], reverse=True):
            if scores[i] <= 0:
                break
            chunk = self.chunks[i]
            if allowed and not allowed.intersection(chunk["engines"]):
                continue
            key = (chunk["doc_id"], chunk["pdf_page"])
            if per_page[key] >= max_per_page:
                continue
            per_page[key] += 1
            results.append({**chunk, "score": round(float(scores[i]), 3)})
            if len(results) >= top_k:
                break
        return results

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump({"chunks": self.chunks}, f)

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        with path.open("rb") as f:
            data = pickle.load(f)
        return cls(data["chunks"])
