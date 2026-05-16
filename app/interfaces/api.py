from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models.schemas import FloodAlertOutput, RunAlertRequest
from app.services.orchestrator import FloodSwarmOrchestrator
from app.settings import get_settings


settings = get_settings()
orchestrator = FloodSwarmOrchestrator(settings=settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await orchestrator.aclose()


app = FastAPI(title="HK Flood Swarm MVP", version="0.1.0", lifespan=lifespan)


@app.post("/runs/flood-alert", response_model=FloodAlertOutput)
async def run_flood_alert(request: RunAlertRequest) -> FloodAlertOutput:
    return await orchestrator.run(mode=request.mode)
