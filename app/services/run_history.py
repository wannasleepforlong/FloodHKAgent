from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.schemas import FloodAlertOutput


class RunHistoryService:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def list_recent_runs(self, *, limit: int = 6) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        for path in sorted(self.log_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            runs.append(
                {
                    "run_id": payload.get("run_id", path.stem),
                    "generated_at": payload.get("generated_at"),
                    "alert_level": payload.get("alert_level"),
                    "overall_risk_score": payload.get("overall_risk_score"),
                    "top_risk_districts": payload.get("top_risk_districts", []),
                    "next_update_priority": payload.get("next_update_priority"),
                    "confidence_overall": payload.get("confidence_overall"),
                }
            )
            if len(runs) >= limit:
                break
        return runs

    def get_run(self, run_id: str) -> FloodAlertOutput:
        path = self.log_dir / f"{run_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return FloodAlertOutput.model_validate(payload)
