"""Прогон агента из командной строки — для отладки и A/B моделей.

Пример:
  python backend/scripts/agent_cli.py B418HK98 S-0009 "Получи результат диагностики"
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import store  # noqa: E402
from app.agent import run_agent  # noqa: E402
from app.config import LLM_MODEL  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vehicle_id")
    parser.add_argument("session_id")
    parser.add_argument("message")
    parser.add_argument("--model", default=None)
    parser.add_argument("--conversation", default=f"cli-{uuid.uuid4().hex[:6]}")
    args = parser.parse_args()

    store.init_db()
    vehicle = store.get_vehicle(args.vehicle_id)
    if not vehicle:
        raise SystemExit(f"нет ТС {args.vehicle_id}")
    result = await run_agent(
        vehicle=vehicle,
        session_id=args.session_id,
        message=args.message,
        conversation_id=args.conversation,
        model=args.model,
    )
    print(f"model: {args.model or LLM_MODEL}")
    print("\n--- инструменты ---")
    for step in result["tool_calls"]:
        print(f"  {step['tool']}({step['arguments']}) -> error={step['error']}")
    print("\n--- ответ ---")
    print(result["reply"])


if __name__ == "__main__":
    asyncio.run(main())
