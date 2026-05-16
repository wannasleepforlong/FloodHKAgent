from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.models.schemas import (
    AlertLevel,
    DistrictScore,
    FloodAlertOutput,
    RecommendedAction,
    SystemHealth,
    UpdatePriority,
)
from app.services.auto_runner import HorizonAutoRunService
from app.settings import get_settings


def _make_output(run_id: str) -> FloodAlertOutput:
    now = datetime.now(UTC)
    return FloodAlertOutput(
        run_id=run_id,
        generated_at=now,
        alert_level=AlertLevel.GREEN,
        overall_risk_score=1.0,
        district_scores={
            "Tuen Mun": DistrictScore(score=1.0, confidence="HIGH", primary_driver="SynthesisAgent")
        },
        compound_flags=[],
        top_risk_districts=["Tuen Mun"],
        narrative_en="Testing narrative.",
        narrative_tc="Testing narrative.",
        recommended_actions=[RecommendedAction(code="MONITOR", description="Monitor closely.")],
        confidence_overall=0.8,
        agent_signals=[],
        compound_detector_output=[],
        data_freshness=now,
        reasoning="Testing reasoning.",
        next_update_priority=UpdatePriority.ROUTINE,
        system_health=SystemHealth(agents_healthy=5),
    )


@pytest.mark.asyncio
async def test_manual_run_arms_scheduler():
    settings = replace(get_settings(), prediction_horizon_minutes=60)
    calls: list[str] = []

    async def fake_run(mode):
        calls.append(mode.value)
        return _make_output("manual-run")

    service = HorizonAutoRunService(settings=settings, run_callback=fake_run)
    try:
        output = await service.run_manual()
        status = service.get_status()
        assert output.run_id == "manual-run"
        assert calls == ["live"]
        assert status["active"] is True
        assert status["horizon_minutes"] == 60
        assert status["next_run_at"] is not None
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_due_auto_run_executes_once_and_rearms():
    settings = replace(get_settings(), prediction_horizon_minutes=60)
    calls: list[str] = []

    async def fake_run(mode):
        calls.append(mode.value)
        return _make_output(f"run-{len(calls)}")

    service = HorizonAutoRunService(settings=settings, run_callback=fake_run)
    try:
        await service.run_manual()
        service._next_run_at = datetime.now(UTC)
        service._signal.set()
        await asyncio.sleep(0.05)

        status = service.get_status()
        assert calls == ["live", "live"]
        assert status["active"] is True
        assert status["next_run_at"] is not None
    finally:
        await service.aclose()
