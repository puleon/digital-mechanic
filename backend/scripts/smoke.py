"""Дымовой прогон стенда: ключевые сценарии через HTTP API.

Запуск:
  python backend/scripts/smoke.py                     # http://127.0.0.1:8090
  python backend/scripts/smoke.py --base https://digital-mechanic.128-0-134-250.sslip.io
  python backend/scripts/smoke.py --with-ticket       # + создание заявки в ТОиР

Проверяет то, что требует ТЗ: вызов диагностики, ответ по руководству со страницей,
отказ при неудачной проверке и (по флагу) заявку с ticket_id.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import uuid

import httpx

ANOMALY_VEHICLE = ("B418HK98", "S-0009")   # F01, клапанный механизм
FAILED_VEHICLE = ("P456AT178", "S-0003")   # check_failed
CITE_RE = re.compile(r"стр\.?\s*(\d+)", re.I)


def chat(base: str, vehicle: str, session: str, message: str, conversation: str) -> dict:
    started = time.time()
    r = httpx.post(
        f"{base}/api/chat",
        json={
            "vehicle_id": vehicle,
            "session_id": session,
            "message": message,
            "conversation_id": conversation,
        },
        timeout=180,
    )
    r.raise_for_status()
    data = r.json()
    data["_seconds"] = round(time.time() - started, 1)
    return data


def tool_names(reply: dict) -> list[str]:
    return [call["tool"] for call in reply.get("tool_calls", [])]


def check(label: str, ok: bool, detail: str = "") -> bool:
    print(f"{'OK  ' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8090")
    parser.add_argument("--with-ticket", action="store_true")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    health = httpx.get(f"{base}/api/health", timeout=20).json()
    if not check("health", health.get("status") == "ok", str(health)):
        return 1

    vehicles = httpx.get(f"{base}/api/vehicles", timeout=20).json()["vehicles"]
    if not check("vehicles", len(vehicles) > 0, f"{len(vehicles)} ТС"):
        return 1

    conversation = f"smoke-{uuid.uuid4().hex[:8]}"
    vehicle, session = ANOMALY_VEHICLE

    reply = chat(base, vehicle, session, "Получить результат диагностики", conversation)
    names = tool_names(reply)
    check("diagnosis: get_diagnosis вызван", "get_diagnosis" in names, ", ".join(names))
    check("diagnosis: ответ не пустой", len(reply["reply"]) > 80, f"{reply['_seconds']} с")

    question = "С каким моментом затягивать болты крепления осей коромысел?"
    reply = chat(base, vehicle, session, question, conversation)
    reply_text = reply["reply"]
    check("rag: search_manuals вызван", "search_manuals" in tool_names(reply))
    found = CITE_RE.search(reply_text)
    check("rag: есть ссылка на страницу", bool(found),
          f"стр. {found.group(1)}, {reply['_seconds']} с" if found else f"{reply['_seconds']} с")
    check("rag: ссылается на руководство ЯМЗ-236", "236" in reply_text)

    reply = chat(base, *FAILED_VEHICLE, "Что показала проверка?", conversation)
    text = reply["reply"].lower()
    check("check_failed: агент не делает вывод о двигателе",
          "не удалось" in text or "повтор" in text or "качество" in text,
          f"{reply['_seconds']} с")

    reply = chat(base, vehicle, session, "Сколько стоит ремонт в рублях?", conversation)
    text = reply["reply"].lower()
    check("вне базы знаний: отказ", "нет данных" in text or "не содержится" in text
          or "нет информации" in text, f"{reply['_seconds']} с")

    if args.with_ticket:
        reply = chat(base, vehicle, session, "Оформи заявку на дефектовку", conversation)
        tickets = [
            call["result"].get("ticket_id")
            for call in reply.get("tool_calls", [])
            if call["tool"] == "create_ticket" and isinstance(call.get("result"), dict)
        ]
        tickets = [t for t in tickets if t]
        check("заявка: ticket_id получен", bool(tickets), ", ".join(tickets) or str(reply["reply"])[:160])

    return 0


if __name__ == "__main__":
    sys.exit(main())
