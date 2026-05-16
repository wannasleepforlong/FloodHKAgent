from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.schemas import FloodAlertOutput, LearningSummary, PredictionValidation
from app.services.utils import abs_minutes_between


class RunHistoryService:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def list_recent_runs(self, *, limit: int = 6) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        for path, payload in self._iter_run_payloads():
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

    def find_prediction_match(
        self,
        *,
        actual_time,
        tolerance_minutes: int,
    ) -> FloodAlertOutput | None:
        best_match: tuple[float, FloodAlertOutput] | None = None
        for _, payload in self._iter_run_payloads():
            try:
                run = FloodAlertOutput.model_validate(payload)
            except Exception:
                continue
            if run.prediction_window is None:
                continue
            delta_minutes = abs_minutes_between(run.prediction_window.target_time, actual_time)
            if delta_minutes > tolerance_minutes:
                continue
            if best_match is None or delta_minutes < best_match[0]:
                best_match = (delta_minutes, run)
        return best_match[1] if best_match is not None else None

    def build_learning_summary(
        self,
        *,
        limit: int = 10,
        pending_validation: PredictionValidation | None = None,
    ) -> LearningSummary | None:
        validations: list[PredictionValidation] = []
        if pending_validation is not None:
            validations.append(pending_validation)

        for _, payload in self._iter_run_payloads():
            validation_payload = payload.get("validation")
            if validation_payload is None:
                continue
            try:
                validation = PredictionValidation.model_validate(validation_payload)
            except Exception:
                continue
            validations.append(validation)
            if len(validations) >= limit:
                break

        if not validations:
            return None

        window = validations[:limit]
        mean_signed_error = round(
            sum(item.risk_score_error for item in window) / len(window),
            3,
        )
        mean_abs_error = round(
            sum(item.abs_risk_score_error for item in window) / len(window),
            3,
        )
        hit_rate = round(
            sum(1 for item in window if item.alert_level_match) / len(window),
            3,
        )
        lessons: list[str] = []
        if mean_signed_error >= 0.5:
            lessons.append("Recent runs have underpredicted realized risk; bias upward when signals are mixed.")
        elif mean_signed_error <= -0.5:
            lessons.append("Recent runs have overpredicted realized risk; trim aggressive escalation when evidence is thin.")
        if hit_rate < 0.6:
            lessons.append("Alert-level agreement is weak; prioritize warning severity and compound-event corroboration.")
        if mean_abs_error > 1.0:
            lessons.append("Calibration error remains elevated; use wider uncertainty framing in close calls.")

        lesson_text = " ".join(lessons[:3]) or "Calibration is stable with no strong corrective lesson yet."
        summary_text = (
            f"Mean signed error: {mean_signed_error:+.3f}. "
            f"Mean absolute error: {mean_abs_error:.3f}. "
            f"Hit rate: {hit_rate:.1%}. "
            f"Lessons: {lesson_text}"
        )
        return LearningSummary(
            source="local",
            summary_text=summary_text,
            recent_validation_count=len(window),
        )

    def _iter_run_payloads(self) -> list[tuple[Path, dict[str, Any]]]:
        payloads: list[tuple[Path, dict[str, Any]]] = []
        for path in sorted(self.log_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            payloads.append((path, payload))
        return payloads
