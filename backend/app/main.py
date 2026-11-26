"""HTTP API приложения."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import agent, store
from .config import ROOT

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    yield


app = FastAPI(title="Цифровой механик", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    vehicle_id: str
    session_id: str
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    model: str | None = None


@app.get("/api/health")
def health():
    return {"status": "ok", "vehicles": len(store.list_vehicles())}


@app.get("/api/vehicles")
def vehicles():
    return {"vehicles": store.list_vehicles()}


@app.get("/api/vehicles/{vehicle_id}")
def vehicle_card(vehicle_id: str):
    vehicle = store.get_vehicle(vehicle_id)
    if not vehicle:
        raise HTTPException(404, "vehicle_id not found")
    return {
        "vehicle": vehicle,
        "sessions": store.get_sessions(vehicle_id),
        "tickets": store.list_tickets(vehicle_id),
    }


@app.get("/api/fleet")
def fleet():
    return store.fleet_overview()


@app.post("/api/chat")
async def chat(req: ChatRequest):
    vehicle = store.get_vehicle(req.vehicle_id)
    if not vehicle:
        raise HTTPException(404, "vehicle_id not found")
    session = store.get_session(req.vehicle_id, req.session_id)
    if not session:
        raise HTTPException(404, "session_id not found for this vehicle")
    conversation_id = req.conversation_id or f"c-{uuid.uuid4().hex[:8]}"
    try:
        result = await agent.run_agent(
            vehicle=vehicle,
            session_id=req.session_id,
            message=req.message,
            conversation_id=conversation_id,
            model=req.model,
        )
    except Exception as exc:  # noqa: BLE001 — наружу отдаём понятную ошибку, детали в лог
        log.exception("сбой обработки сообщения (%s)", req.vehicle_id)
        raise HTTPException(
            503, "Модель недоступна. Попробуйте ещё раз через минуту."
        ) from exc
    result["conversation_id"] = conversation_id
    return result


# Собранный фронтенд (в dev его нет — там Vite на 5173).
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        candidate = DIST / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
