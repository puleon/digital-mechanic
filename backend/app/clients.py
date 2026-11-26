"""HTTP-клиенты внешних сервисов. Адреса — только из конфигурации (.env)."""
from __future__ import annotations

import httpx

from .config import MOCK_ML_URL, MOCK_TOIR_URL


class ServiceError(RuntimeError):
    def __init__(self, service: str, status_code: int, detail: str):
        super().__init__(f"{service}: HTTP {status_code}: {detail}")
        self.service = service
        self.status_code = status_code
        self.detail = detail


async def diagnose(vehicle_id: str, session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{MOCK_ML_URL}/diagnose",
            json={"vehicle_id": vehicle_id, "session_id": session_id},
        )
    if r.status_code != 200:
        raise ServiceError("ML", r.status_code, r.text[:300])
    return r.json()


async def create_ticket(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{MOCK_TOIR_URL}/tickets", json=payload)
    if r.status_code != 201:
        raise ServiceError("ТОиР", r.status_code, r.text[:300])
    return r.json()
