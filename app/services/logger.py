from __future__ import annotations

from pathlib import Path

from app.models.schemas import FloodAlertOutput


class RunLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def write(self, output: FloodAlertOutput) -> Path:
        path = self.log_dir / f"{output.run_id}.json"
        path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
        return path
