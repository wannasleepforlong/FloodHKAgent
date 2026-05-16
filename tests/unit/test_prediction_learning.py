from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.models.schemas import (
    AlertLevel,
    DistrictScore,
    FloodAlertOutput,
    LearningSummary,
    PredictionValidation,
    PredictionWindow,
    RecommendedAction,
    SystemHealth,
    LettaLearningDetails,
    UpdatePriority,
)
from app.services.prediction_learning import PredictionLearningService
from app.services.run_history import RunHistoryService
from app.settings import get_settings


def _make_run(
    *,
    run_id: str,
    generated_at: datetime,
    score: float,
    alert_level: AlertLevel,
    target_time: datetime | None = None,
):
    output = FloodAlertOutput(
        run_id=run_id,
        generated_at=generated_at,
        alert_level=alert_level,
        overall_risk_score=score,
        district_scores={
            "Tuen Mun": DistrictScore(score=score, confidence="HIGH", primary_driver="SynthesisAgent")
        },
        compound_flags=[],
        top_risk_districts=["Tuen Mun"],
        narrative_en="Testing narrative.",
        narrative_tc="Testing narrative.",
        recommended_actions=[RecommendedAction(code="MONITOR", description="Monitor closely.")],
        confidence_overall=0.8,
        agent_signals=[],
        compound_detector_output=[],
        data_freshness=generated_at,
        reasoning="Testing reasoning.",
        next_update_priority=UpdatePriority.ROUTINE,
        system_health=SystemHealth(agents_healthy=5),
        prediction_window=(
            PredictionWindow(
                predicted_at=generated_at,
                target_time=target_time,
                target_horizon_minutes=180,
                matching_tolerance_minutes=5,
                predicted_overall_risk_score=score,
                predicted_alert_level=alert_level,
                predicted_confidence=0.8,
                prediction_reasoning_summary="Testing reasoning.",
            )
            if target_time is not None
            else None
        ),
    )
    return output


def test_run_history_finds_closest_prediction_match(tmp_path):
    history = RunHistoryService(tmp_path)
    actual_time = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
    farther = _make_run(
        run_id="farther",
        generated_at=actual_time - timedelta(hours=3, minutes=2),
        score=4.0,
        alert_level=AlertLevel.YELLOW,
        target_time=actual_time - timedelta(minutes=2),
    )
    closer = _make_run(
        run_id="closer",
        generated_at=actual_time - timedelta(hours=3, minutes=1),
        score=5.0,
        alert_level=AlertLevel.AMBER,
        target_time=actual_time + timedelta(minutes=1),
    )
    for run in (farther, closer):
        (tmp_path / f"{run.run_id}.json").write_text(run.model_dump_json(indent=2), encoding="utf-8")

    matched = history.find_prediction_match(actual_time=actual_time, tolerance_minutes=5)
    assert matched is not None
    assert matched.run_id == "closer"


def test_run_history_returns_none_when_no_prediction_match(tmp_path):
    history = RunHistoryService(tmp_path)
    actual_time = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
    prior = _make_run(
        run_id="prior",
        generated_at=actual_time - timedelta(hours=3),
        score=4.0,
        alert_level=AlertLevel.YELLOW,
        target_time=actual_time + timedelta(minutes=12),
    )
    (tmp_path / "prior.json").write_text(prior.model_dump_json(indent=2), encoding="utf-8")

    assert history.find_prediction_match(actual_time=actual_time, tolerance_minutes=5) is None


def test_run_history_recent_runs_include_learning_details(tmp_path):
    history = RunHistoryService(tmp_path)
    run = _make_run(
        run_id="recent",
        generated_at=datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
        score=5.0,
        alert_level=AlertLevel.YELLOW,
    )
    run.learning_summary = LearningSummary(
        source="letta+local",
        summary_text="Recent calibration summary.",
        recent_validation_count=2,
    )
    run.letta_learning = LettaLearningDetails(
        enabled=True,
        summary_requested=True,
        summary_source="letta+local",
        summary_fetch_succeeded=True,
        summary_text="Recent calibration summary.",
        lesson_store_attempted=False,
    )
    (tmp_path / "recent.json").write_text(run.model_dump_json(indent=2), encoding="utf-8")

    recent_runs = history.list_recent_runs(limit=1)
    assert len(recent_runs) == 1
    assert recent_runs[0]["learning_summary"]["source"] == "letta+local"
    assert recent_runs[0]["letta_learning"]["summary_fetch_succeeded"] is True


def test_run_history_skips_malformed_log_and_builds_summary(tmp_path):
    history = RunHistoryService(tmp_path)
    (tmp_path / "broken.json").write_text("{not-json", encoding="utf-8")

    validated = _make_run(
        run_id="validated",
        generated_at=datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
        score=6.0,
        alert_level=AlertLevel.AMBER,
    )
    validated.validation = PredictionValidation(
        matched_run_id="prior",
        matched_predicted_at=datetime(2026, 5, 16, 9, 0, tzinfo=UTC),
        actual_generated_at=validated.generated_at,
        target_time=datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
        time_delta_minutes=0.0,
        risk_score_error=1.25,
        abs_risk_score_error=1.25,
        alert_level_match=False,
        within_tolerance=True,
    )
    (tmp_path / "validated.json").write_text(
        validated.model_dump_json(indent=2),
        encoding="utf-8",
    )

    summary = history.build_learning_summary(limit=10)
    assert summary is not None
    assert summary.source == "local"
    assert summary.recent_validation_count == 1
    assert "Mean signed error" in summary.summary_text


def test_prediction_learning_builds_validation_and_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOOD_SWARM_PREDICTION_HORIZON_MINUTES", "180")
    monkeypatch.setenv("FLOOD_SWARM_MATCH_TOLERANCE_MINUTES", "5")
    settings = get_settings()
    history = RunHistoryService(tmp_path)
    service = PredictionLearningService(settings=settings, run_history=history)

    prior_generated_at = datetime(2026, 5, 16, 9, 0, tzinfo=UTC)
    prior = _make_run(
        run_id="prior",
        generated_at=prior_generated_at,
        score=4.5,
        alert_level=AlertLevel.YELLOW,
        target_time=datetime(2026, 5, 16, 12, 2, tzinfo=UTC),
    )
    (tmp_path / "prior.json").write_text(prior.model_dump_json(indent=2), encoding="utf-8")

    current = _make_run(
        run_id="current",
        generated_at=datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
        score=6.0,
        alert_level=AlertLevel.AMBER,
    )

    outcome = __import__("asyncio").run(service.finalize_run(current))
    assert outcome.validation is not None
    assert outcome.validation.matched_run_id == "prior"
    assert outcome.validation.within_tolerance is True
    assert outcome.validation.risk_score_error == 1.5
    assert outcome.learning_summary is not None
    assert outcome.learning_summary.recent_validation_count == 1
    assert "Mean signed error" in outcome.learning_summary.summary_text
    assert current.learning_summary is not None
    assert current.letta_learning is not None
    assert current.letta_learning.summary_source == "local"
    assert current.letta_learning.lesson_store_attempted is True
    assert current.letta_learning.lesson_store_succeeded is False


def test_prediction_learning_degrades_gracefully_when_letta_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOOD_SWARM_PREDICTION_HORIZON_MINUTES", "180")
    monkeypatch.setenv("FLOOD_SWARM_MATCH_TOLERANCE_MINUTES", "5")
    settings = get_settings()
    history = RunHistoryService(tmp_path)

    class FailingLettaClient:
        enabled = True

        async def fetch_learning_summary(self):
            raise RuntimeError("fetch failed")

        async def store_validation_lesson(self, lesson_text: str):
            raise RuntimeError("store failed")

    service = PredictionLearningService(
        settings=settings,
        run_history=history,
        letta_client=FailingLettaClient(),
    )

    prior_generated_at = datetime(2026, 5, 16, 9, 0, tzinfo=UTC)
    prior = _make_run(
        run_id="prior",
        generated_at=prior_generated_at,
        score=4.5,
        alert_level=AlertLevel.YELLOW,
        target_time=datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
    )
    (tmp_path / "prior.json").write_text(prior.model_dump_json(indent=2), encoding="utf-8")

    current = _make_run(
        run_id="current",
        generated_at=datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
        score=6.0,
        alert_level=AlertLevel.AMBER,
    )

    summary = __import__("asyncio").run(service.get_learning_summary())
    assert summary is None

    outcome = __import__("asyncio").run(service.finalize_run(current))
    assert outcome.validation is not None
    assert current.prediction_window is not None
    assert current.validation is not None
    assert current.letta_learning is not None
    assert current.letta_learning.summary_fetch_succeeded is False
    assert current.letta_learning.lesson_store_succeeded is False


def test_prediction_learning_prefers_local_summary_when_letta_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOOD_SWARM_PREDICTION_HORIZON_MINUTES", "180")
    monkeypatch.setenv("FLOOD_SWARM_MATCH_TOLERANCE_MINUTES", "5")
    settings = get_settings()
    history = RunHistoryService(tmp_path)

    validated = _make_run(
        run_id="validated",
        generated_at=datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
        score=6.0,
        alert_level=AlertLevel.AMBER,
    )
    validated.validation = PredictionValidation(
        matched_run_id="prior",
        matched_predicted_at=datetime(2026, 5, 16, 9, 0, tzinfo=UTC),
        actual_generated_at=validated.generated_at,
        target_time=datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
        time_delta_minutes=0.0,
        risk_score_error=-0.5,
        abs_risk_score_error=0.5,
        alert_level_match=True,
        within_tolerance=True,
    )
    (tmp_path / "validated.json").write_text(validated.model_dump_json(indent=2), encoding="utf-8")

    service = PredictionLearningService(
        settings=settings,
        run_history=history,
        letta_client=SimpleNamespace(enabled=False),
    )
    summary = __import__("asyncio").run(service.get_learning_summary())
    assert summary is not None
    assert summary.source == "local"


def test_run_history_builds_accuracy_report(tmp_path):
    history = RunHistoryService(tmp_path)
    validated = _make_run(
        run_id="validated",
        generated_at=datetime(2026, 5, 16, 12, 15, tzinfo=UTC),
        score=6.0,
        alert_level=AlertLevel.AMBER,
        target_time=datetime(2026, 5, 16, 13, 15, tzinfo=UTC),
    )
    validated.validation = PredictionValidation(
        matched_run_id="prior",
        matched_predicted_at=datetime(2026, 5, 16, 11, 15, tzinfo=UTC),
        actual_generated_at=validated.generated_at,
        target_time=validated.generated_at,
        time_delta_minutes=0.0,
        risk_score_error=1.0,
        abs_risk_score_error=1.0,
        alert_level_match=True,
        within_tolerance=True,
    )
    validated.learning_summary = LearningSummary(
        source="letta+local",
        summary_text="Compact Letta-backed calibration summary.",
        recent_validation_count=1,
    )
    validated.letta_learning = LettaLearningDetails(
        enabled=True,
        summary_requested=True,
        summary_source="letta+local",
        summary_fetch_succeeded=True,
        summary_text="Compact Letta-backed calibration summary.",
        lesson_store_attempted=True,
        lesson_store_succeeded=True,
        lesson_store_acknowledgement="Stored.",
    )
    (tmp_path / "validated.json").write_text(validated.model_dump_json(indent=2), encoding="utf-8")

    report = history.build_accuracy_report()
    assert report["point_count"] == 1
    assert report["rolling_accuracy_percent"] == 93.0
    assert report["points"][0]["risk_accuracy_percent"] == 90.0
    assert report["points"][0]["alert_accuracy_percent"] == 100.0
    assert report["points"][0]["learning_source"] == "letta+local"
    assert report["points"][0]["letta_summary_source"] == "letta+local"
    assert report["points"][0]["letta_lesson_store_succeeded"] is True
