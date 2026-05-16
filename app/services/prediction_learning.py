from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import FloodAlertOutput, LearningSummary, PredictionValidation, PredictionWindow
from app.services.letta import LettaLearningClient
from app.services.run_history import RunHistoryService
from app.services.utils import abs_minutes_between, add_minutes
from app.settings import Settings


@dataclass
class LearningOutcome:
    prediction_window: PredictionWindow
    validation: PredictionValidation | None
    learning_summary: LearningSummary | None


class PredictionLearningService:
    def __init__(
        self,
        *,
        settings: Settings,
        run_history: RunHistoryService,
        letta_client: LettaLearningClient | None = None,
    ):
        self.settings = settings
        self.run_history = run_history
        self.letta_client = letta_client or LettaLearningClient(settings)

    async def get_learning_summary(self) -> LearningSummary | None:
        local_summary = self.run_history.build_learning_summary(limit=10)
        if self.letta_client.enabled:
            try:
                letta_text = await self.letta_client.fetch_learning_summary()
            except Exception as exc:  # pragma: no cover - depends on remote runtime
                print(f"[learning][letta] summary fetch failed: {exc}")
            else:
                if letta_text:
                    print("[learning] using Letta-backed summary for prompt injection")
                    if local_summary is None:
                        return LearningSummary(
                            source="letta",
                            summary_text=letta_text,
                            recent_validation_count=0,
                        )
                    return local_summary.model_copy(
                        update={"source": "letta+local", "summary_text": letta_text}
                    )
        if local_summary is not None:
            print("[learning] using local validation summary for prompt injection")
        return local_summary

    async def finalize_run(self, output: FloodAlertOutput) -> LearningOutcome:
        prediction_window = self.build_prediction_window(output)
        validation = self._validate_against_history(output, prediction_window)
        output.prediction_window = prediction_window
        output.validation = validation
        learning_summary = self.run_history.build_learning_summary(limit=10, pending_validation=validation)
        if validation is not None:
            print(
                "[learning] validated prior prediction "
                f"run={validation.matched_run_id} error={validation.risk_score_error:.2f} "
                f"delta_min={validation.time_delta_minutes:.2f}"
            )
            await self._store_lesson(validation=validation, output=output, summary=learning_summary)
        else:
            print("[learning] no prior prediction matched current run time")
        return LearningOutcome(
            prediction_window=prediction_window,
            validation=validation,
            learning_summary=learning_summary,
        )

    def build_prediction_window(self, output: FloodAlertOutput) -> PredictionWindow:
        target_time = add_minutes(output.generated_at, self.settings.prediction_horizon_minutes)
        summary = output.reasoning[:240].strip() if output.reasoning else None
        print(
            "[learning] building prediction window "
            f"target={target_time.isoformat()} horizon_min={self.settings.prediction_horizon_minutes}"
        )
        return PredictionWindow(
            predicted_at=output.generated_at,
            target_time=target_time,
            target_horizon_minutes=self.settings.prediction_horizon_minutes,
            matching_tolerance_minutes=self.settings.prediction_matching_tolerance_minutes,
            predicted_overall_risk_score=output.overall_risk_score,
            predicted_alert_level=output.alert_level,
            predicted_confidence=output.confidence_overall,
            prediction_reasoning_summary=summary,
        )

    def _validate_against_history(
        self, output: FloodAlertOutput, prediction_window: PredictionWindow
    ) -> PredictionValidation | None:
        matched = self.run_history.find_prediction_match(
            actual_time=output.generated_at,
            tolerance_minutes=self.settings.prediction_matching_tolerance_minutes,
        )
        if matched is None or matched.prediction_window is None:
            return None
        delta_minutes = abs_minutes_between(matched.prediction_window.target_time, output.generated_at)
        risk_score_error = round(output.overall_risk_score - matched.prediction_window.predicted_overall_risk_score, 3)
        return PredictionValidation(
            matched_run_id=matched.run_id,
            matched_predicted_at=matched.prediction_window.predicted_at,
            actual_generated_at=output.generated_at,
            target_time=matched.prediction_window.target_time,
            time_delta_minutes=round(delta_minutes, 3),
            risk_score_error=risk_score_error,
            abs_risk_score_error=round(abs(risk_score_error), 3),
            alert_level_match=output.alert_level == matched.prediction_window.predicted_alert_level,
            within_tolerance=delta_minutes <= prediction_window.matching_tolerance_minutes,
        )

    async def _store_lesson(
        self,
        *,
        validation: PredictionValidation,
        output: FloodAlertOutput,
        summary: LearningSummary | None,
    ) -> None:
        if not self.letta_client.enabled:
            print("[learning][letta] skipped memory write because Letta is not configured")
            return
        lesson = self._format_lesson(validation=validation, output=output, summary=summary)
        try:
            acknowledgement = await self.letta_client.store_validation_lesson(lesson)
        except Exception as exc:  # pragma: no cover - depends on remote runtime
            print(f"[learning][letta] lesson write failed: {exc}")
            return
        print(f"[learning][letta] ack={acknowledgement or 'no acknowledgement text'}")

    def _format_lesson(
        self,
        *,
        validation: PredictionValidation,
        output: FloodAlertOutput,
        summary: LearningSummary | None,
    ) -> str:
        summary_text = summary.summary_text if summary is not None else "No rolling summary available yet."
        return (
            f"Validation lesson for flood-horizon calibration:\n"
            f"- predicted_at: {validation.matched_predicted_at.isoformat()}\n"
            f"- target_time: {validation.target_time.isoformat()}\n"
            f"- actual_generated_at: {validation.actual_generated_at.isoformat()}\n"
            f"- predicted_alert_level_match: {validation.alert_level_match}\n"
            f"- risk_score_error: {validation.risk_score_error}\n"
            f"- abs_risk_score_error: {validation.abs_risk_score_error}\n"
            f"- actual_alert_level: {output.alert_level.value}\n"
            f"- actual_overall_risk_score: {output.overall_risk_score}\n"
            f"- top_risk_districts: {', '.join(output.top_risk_districts)}\n"
            f"- current_rolling_summary: {summary_text}\n"
            f"- operator_narrative: {output.narrative_en}"
        )
