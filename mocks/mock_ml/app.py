"""Mock ML API: отдаёт результат акустической проверки по vehicle_id и session_id.

Запуск: uvicorn mock_ml.app:app --port 8001
Данные читаются из data/vehicles.json; другой файл задаётся переменной MOCK_DATA_PATH.
"""
import json
import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.environ.get("MOCK_DATA_PATH", os.path.join(ROOT, "data", "vehicles.json"))


class DiagnoseRequest(BaseModel):
    vehicle_id: str = Field(min_length=1, examples=["M333YK47"])
    session_id: str = Field(min_length=1, examples=["S-0005"])


class DiagnoseResponse(BaseModel):
    vehicle_id: str
    session_id: str
    status: Literal["normal", "anomaly", "check_failed"]
    anomaly_type: Optional[str] = Field(pattern=r"^F(0[1-9]|1[0-4])$", description="F01…F14 или null")
    anomaly_title: Optional[str]
    anomaly_score: Optional[float] = Field(ge=0, le=1)
    confidence: Optional[float] = Field(ge=0, le=1)
    signal_quality: Literal["good", "warning", "bad"]
    description: str
    model_version: str


def load_sessions(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    vehicles = {v["vehicle_id"] for v in data["vehicles"]}
    sessions = {}
    for v in data["vehicles"]:
        for s in v["sessions"]:
            sessions[(v["vehicle_id"], s["session_id"])] = {k: s[k] for k in DiagnoseResponse.model_fields}
    return vehicles, sessions


VEHICLES, SESSIONS = load_sessions(DATA_PATH)

app = FastAPI(
    title="НейроДВС Mock ML API",
    version="mock-v1",
    description="Заглушка сервиса акустической диагностики ДВС для хакатона «ИИкузница». Данные синтетические.",
)
# Заглушка открыта для запросов из браузера с любого адреса: это тестовый сервис без секретов.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-ml", "vehicles": len(VEHICLES), "sessions": len(SESSIONS)}


@app.post("/diagnose", response_model=DiagnoseResponse,
          responses={404: {"description": "Неизвестный vehicle_id или session_id"}})
def diagnose(req: DiagnoseRequest):
    if req.vehicle_id not in VEHICLES:
        raise HTTPException(status_code=404, detail="vehicle_id not found")
    result = SESSIONS.get((req.vehicle_id, req.session_id))
    if result is None:
        raise HTTPException(status_code=404, detail="session_id not found for this vehicle_id")
    return result
