"""Настройки приложения. Все внешние адреса задаются через окружение (F6 ТЗ)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    p = Path(value)
    return p if p.is_absolute() else (ROOT / p)


DATA_DIR = _path(os.getenv("DATA_DIR"), ROOT / "data")
MANUALS_DIR = _path(os.getenv("MANUALS_DIR"), ROOT / "manuals")
INDEX_DIR = DATA_DIR / "index"

MOCK_ML_URL = os.getenv("MOCK_ML_URL", "http://127.0.0.1:8001").rstrip("/")
MOCK_TOIR_URL = os.getenv("MOCK_TOIR_URL", "http://127.0.0.1:8002").rstrip("/")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.proxyapi.ru/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-v4.1-flash-1017")
