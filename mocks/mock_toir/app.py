"""Mock ТОиР: принимает заявку на дефектовку и возвращает номер заявки.

Запуск: uvicorn mock_toir.app:app --port 8002
Заявки хранятся в памяти процесса, после перезапуска нумерация начинается с TKT-0001.
"""
import itertools
import json
import os
import threading
from typing import List, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.environ.get("MOCK_DATA_PATH", os.path.join(ROOT, "data", "vehicles.json"))


class Reference(BaseModel):
    manual: str = Field(min_length=1, description="Название или обозначение документа", examples=["236-3902150-Б РЭ"])
    pdf_page: int = Field(ge=1, description="Номер страницы PDF")


class TicketRequest(BaseModel):
    vehicle_id: str = Field(min_length=1, examples=["M333YK47"])
    session_id: str = Field(min_length=1, examples=["S-0005"])
    anomaly_type: str = Field(pattern=r"^F(0[1-9]|1[0-4])$", description="Значение anomaly_type из ответа /diagnose")
    conclusion: str = Field(min_length=1, description="Диагноз")
    urgency: Literal["low", "medium", "high"] = Field(description="Приоритет")
    operations: List[str] = Field(min_length=1, description="Работы")
    spare_parts: List[str] = Field(description="Запчасти, список может быть пустым")
    references: List[Reference] = Field(min_length=1, description="Ссылки на источники")


class TicketResponse(BaseModel):
    ticket_id: str
    status: Literal["created"]


def load_index(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {v["vehicle_id"]: {s["session_id"] for s in v["sessions"]} for v in data["vehicles"]}


INDEX = load_index(DATA_PATH)
_counter = itertools.count(1)
_lock = threading.Lock()
TICKETS = []

app = FastAPI(
    title="НейроДВС Mock ТОиР",
    version="mock-v1",
    description="Заглушка системы технического обслуживания и ремонта для хакатона «ИИкузница».",
)
# Заглушка открыта для запросов из браузера с любого адреса: это тестовый сервис без секретов.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# Прежние имена полей заявки. В контракт они не входят, действуют имена из раздела 5 ТЗ версии 6.
LEGACY_FIELDS = ("fault_id", "diagnosis", "priority", "works", "parts", "source_pages")
LEGACY_REFERENCE_FIELDS = ("document", "page")


def legacy_fields(body):
    if not isinstance(body, dict):
        return []
    found = [k for k in LEGACY_FIELDS if k in body]
    refs = body.get("references")
    for item in refs if isinstance(refs, list) else []:
        if isinstance(item, dict):
            found += [k for k in LEGACY_REFERENCE_FIELDS if k in item and k not in found]
    return found


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    found = legacy_fields(exc.body) if request.url.path == "/tickets" else []
    if not found:
        return await request_validation_exception_handler(request, exc)
    return JSONResponse(status_code=418, content={
        "detail": "Я чайник. Заявка собрана по прежней схеме, действует контракт из раздела 5 ТЗ версии 6. "
                  "Механик заварил чай и ждёт заявку по ТЗ.",
        "legacy_fields": found,
    })


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-toir", "tickets": len(TICKETS)}


@app.post("/tickets", response_model=TicketResponse, status_code=201,
          responses={404: {"description": "Неизвестный vehicle_id или session_id"}})
def create_ticket(req: TicketRequest):
    if req.vehicle_id not in INDEX:
        raise HTTPException(status_code=404, detail="vehicle_id not found")
    if req.session_id not in INDEX[req.vehicle_id]:
        raise HTTPException(status_code=404, detail="session_id not found for this vehicle_id")
    with _lock:
        ticket_id = f"TKT-{next(_counter):04d}"
        TICKETS.append({"ticket_id": ticket_id, **req.model_dump()})
    return {"ticket_id": ticket_id, "status": "created"}
