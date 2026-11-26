"""Серверная валидация заявки в ТОиР: нельзя ссылаться на непросмотренные страницы."""
from __future__ import annotations

import asyncio

import pytest

from app import agent, store
from app.config import INDEX_DIR

pytestmark = pytest.mark.skipif(
    not (INDEX_DIR / "bm25.pkl").exists(),
    reason="индекс не собран: python backend/scripts/ingest.py",
)

MANUAL = "236.01.01 РК"


def make_ctx(seen: set[tuple[str, int]] | None = None) -> agent.AgentContext:
    ctx = agent.AgentContext(
        {"vehicle_id": "S-0009", "garage_no": "А-001", "make": "МАЗ", "model": "5337",
         "engine_model": "ЯМЗ-236М2", "fuel": "ДТ"},
        "S-0009",
    )
    ctx.seen_pages = seen or set()
    return ctx


ARGS = {
    "anomaly_type": "F08",
    "conclusion": "Повышенный расход масла, требуется дефектовка",
    "urgency": "medium",
    "operations": ["Проверить клапанный механизм", "Замерить зазоры"],
    "spare_parts": ["Прокладка клапанной крышки"],
    "references": [{"manual": MANUAL, "pdf_page": 269}],
}


@pytest.fixture()
def anomaly(monkeypatch):
    monkeypatch.setattr(
        store, "get_session",
        lambda vehicle_id, session_id: {"vehicle_id": vehicle_id, "session_id": session_id,
                                        "status": "anomaly", "anomaly_type": "F08"},
    )
    created = {}

    async def fake_create(payload):
        created["payload"] = payload
        return {"ticket_id": "TKT-9001", "status": "created"}

    monkeypatch.setattr(agent.clients, "create_ticket", fake_create)
    monkeypatch.setattr(store, "save_ticket", lambda ticket_id, payload: None)
    return created


def run(args, ctx):
    return asyncio.run(agent._create_ticket(args, ctx))


def test_page_not_seen_in_search_is_rejected(anomaly):
    with pytest.raises(agent.ToolError, match="не встречалась"):
        run(ARGS, make_ctx())
    assert "payload" not in anomaly


def test_page_from_other_engine_is_rejected(anomaly):
    with pytest.raises(agent.ToolError, match="не относится к двигателю"):
        run({**ARGS, "references": [{"manual": "536.3902150 РЭ", "pdf_page": 271}]},
            make_ctx({("536.3902150 РЭ", 271)}))


def test_page_beyond_document_is_rejected(anomaly):
    with pytest.raises(agent.ToolError, match="нет в документе"):
        run({**ARGS, "references": [{"manual": MANUAL, "pdf_page": 10**6}]},
            make_ctx({(MANUAL, 10**6)}))


def test_seen_page_is_accepted(anomaly):
    result = run(ARGS, make_ctx({(MANUAL, 269)}))
    assert result["ticket_id"] == "TKT-9001"
    assert anomaly["payload"]["references"] == [{"manual": MANUAL, "pdf_page": 269}]
    assert result["payload"]["anomaly_type"] == "F08"


def test_wrong_anomaly_type_is_rejected(anomaly):
    with pytest.raises(agent.ToolError, match="anomaly_type"):
        run({**ARGS, "anomaly_type": "F01"}, make_ctx({(MANUAL, 269)}))


def test_ticket_requires_anomaly_status(monkeypatch):
    monkeypatch.setattr(
        store, "get_session",
        lambda vehicle_id, session_id: {"status": "normal", "anomaly_type": None},
    )
    with pytest.raises(agent.ToolError, match="только при отклонении"):
        run(ARGS, make_ctx({(MANUAL, 269)}))


def test_empty_operations_rejected(anomaly):
    with pytest.raises(agent.ToolError, match="operations"):
        run({**ARGS, "operations": []}, make_ctx({(MANUAL, 269)}))
