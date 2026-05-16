from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models.schemas import FloodAlertOutput, RunAlertRequest
from app.services.auto_runner import HorizonAutoRunService
from app.services.orchestrator import FloodSwarmOrchestrator
from app.services.run_history import RunHistoryService
from app.settings import get_settings


settings = get_settings()
orchestrator = FloodSwarmOrchestrator(settings=settings)
auto_runner = HorizonAutoRunService(settings=settings, run_callback=orchestrator.run)
run_history = RunHistoryService(settings.log_dir)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
data_dir = Path(__file__).resolve().parent.parent.parent / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await auto_runner.aclose()
    await orchestrator.aclose()


app = FastAPI(title="HK Flood Swarm MVP", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
app.mount("/data", StaticFiles(directory=data_dir), name="data")


@app.get("/", response_class=FileResponse)
async def dashboard() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.post("/runs/flood-alert", response_model=FloodAlertOutput)
async def run_flood_alert(request: RunAlertRequest) -> FloodAlertOutput:
    return await auto_runner.run_manual(mode=request.mode)


@app.get("/api/runs/schedule")
async def get_schedule_status() -> dict[str, object]:
    return auto_runner.get_status()


@app.get("/api/runs/recent")
async def recent_runs() -> dict[str, list[dict[str, object]]]:
    return {"runs": run_history.list_recent_runs()}


@app.get("/api/runs/{run_id}", response_model=FloodAlertOutput)
async def get_run(run_id: str) -> FloodAlertOutput:
    try:
        return run_history.get_run(run_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Run not found") from error
