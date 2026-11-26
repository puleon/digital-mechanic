"""SQLite-хранилище: парк, проверки, заявки, история диалогов.

Память по vehicle_id (B1) живёт здесь, а не в памяти процесса: переживает перезапуск.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR

DB_PATH = DATA_DIR / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id TEXT PRIMARY KEY,
    garage_no TEXT,
    make TEXT,
    model TEXT,
    vehicle_type TEXT,
    engine_model TEXT NOT NULL,
    fuel TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    vehicle_id TEXT NOT NULL REFERENCES vehicles(vehicle_id),
    checked_at TEXT,
    status TEXT NOT NULL,
    anomaly_type TEXT,
    anomaly_title TEXT,
    anomaly_score REAL,
    confidence REAL,
    signal_quality TEXT,
    description TEXT,
    model_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_vehicle ON sessions(vehicle_id, checked_at);
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    vehicle_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    anomaly_type TEXT,
    conclusion TEXT,
    urgency TEXT,
    operations TEXT,
    spare_parts TEXT,
    references_json TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    vehicle_id TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, id);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
        if count:
            return
        payload = json.loads((DATA_DIR / "vehicles.json").read_text(encoding="utf-8"))
        for v in payload["vehicles"]:
            conn.execute(
                "INSERT INTO vehicles VALUES (?,?,?,?,?,?,?)",
                (v["vehicle_id"], v["garage_no"], v["make"], v["model"],
                 v["vehicle_type"], v["engine_model"], v["fuel"]),
            )
            for s in v["sessions"]:
                conn.execute(
                    "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (s["session_id"], v["vehicle_id"], s["checked_at"], s["status"],
                     s["anomaly_type"], s["anomaly_title"], s["anomaly_score"],
                     s["confidence"], s["signal_quality"], s["description"],
                     s["model_version"]),
                )


def _row(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def get_vehicle(vehicle_id: str) -> dict | None:
    with connect() as conn:
        return _row(conn.execute(
            "SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,)
        ).fetchone())


def list_vehicles() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("""
            SELECT v.*, s.session_id, s.checked_at, s.status, s.anomaly_type,
                   s.anomaly_title, s.anomaly_score, s.confidence, s.signal_quality
            FROM vehicles v
            LEFT JOIN sessions s ON s.session_id = (
                SELECT session_id FROM sessions
                WHERE vehicle_id = v.vehicle_id
                ORDER BY checked_at DESC LIMIT 1
            )
            ORDER BY v.garage_no
        """).fetchall()
        return [dict(r) for r in rows]


def get_sessions(vehicle_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE vehicle_id = ? ORDER BY checked_at",
            (vehicle_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_session(vehicle_id: str, session_id: str) -> dict | None:
    with connect() as conn:
        return _row(conn.execute(
            "SELECT * FROM sessions WHERE vehicle_id = ? AND session_id = ?",
            (vehicle_id, session_id),
        ).fetchone())


def add_message(conversation_id: str, vehicle_id: str | None, role: str, content: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, vehicle_id, role, content, created_at)"
            " VALUES (?,?,?,?,?)",
            (conversation_id, vehicle_id, role, content, datetime.now(timezone.utc).isoformat()),
        )


def get_messages(conversation_id: str, limit: int = 12) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ?"
            " ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def save_ticket(ticket_id: str, payload: dict) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ticket_id, payload["vehicle_id"], payload["session_id"],
             payload.get("anomaly_type"), payload.get("conclusion"),
             payload.get("urgency"), json.dumps(payload.get("operations", []), ensure_ascii=False),
             json.dumps(payload.get("spare_parts", []), ensure_ascii=False),
             json.dumps(payload.get("references", []), ensure_ascii=False),
             datetime.now(timezone.utc).isoformat()),
        )


def list_tickets(vehicle_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE vehicle_id = ? ORDER BY created_at DESC",
            (vehicle_id,),
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["operations"] = json.loads(item.pop("operations") or "[]")
            item["spare_parts"] = json.loads(item.pop("spare_parts") or "[]")
            item["references"] = json.loads(item.pop("references_json") or "[]")
            result.append(item)
        return result


def fleet_overview() -> dict:
    """Сводка по парку для главного механика (B3)."""
    vehicles = list_vehicles()
    buckets = {"ok": [], "attention": [], "quarantine": []}
    for v in vehicles:
        status = v.get("status")
        score = v.get("anomaly_score") or 0.0
        if status == "normal":
            bucket = "ok"
        elif status == "check_failed":
            bucket = "attention"
        elif score >= 0.75:
            bucket = "quarantine"
        else:
            bucket = "attention"
        v["bucket"] = bucket
        buckets[bucket].append(v)

    for bucket in buckets.values():
        bucket.sort(key=lambda x: (x.get("anomaly_score") or 0), reverse=True)

    return {
        "total": len(vehicles),
        "counts": {k: len(v) for k, v in buckets.items()},
        "buckets": buckets,
    }
