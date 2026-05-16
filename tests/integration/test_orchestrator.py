from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.schemas import (
    AgentAssessment,
    AlertLevel,
    CompoundAssessment,
    CompoundFlag,
    DistrictScore,
    RecommendedAction,
    SynthesisAssessment,
    UpdatePriority,
)
from app.services.orchestrator import FloodSwarmOrchestrator
from app.settings import get_settings


class FakeHKOClient:
    async def aclose(self):
        return None

    async def get_hourly_rainfall(self):
        return {
            "obsTime": "2026-05-16T08:00:00Z",
            "hourlyRainfall": [
                {
                    "automaticWeatherStation": "Tuen Mun",
                    "automaticWeatherStationID": "RF019",
                    "value": "12",
                    "unit": "mm",
                }
            ],
        }

    async def get_tide_bundle(self, now):
        return {
            "as_of": "2026-05-16T08:00:00Z",
            "stations": {
                "QUB": {"hhot": {"fields": ["height"], "data": [[2.0]]}, "hlt": {"fields": [], "data": []}},
                "TBT": {"hhot": {"fields": ["height"], "data": [[1.9]]}, "hlt": {"fields": [], "data": []}},
                "CCH": {"hhot": {"fields": ["height"], "data": [[1.7]]}, "hlt": {"fields": [], "data": []}},
            },
        }

    async def get_warning_summary(self):
        return {
            "WRAIN": {
                "name": "Black Rainstorm Warning Signal",
                "code": "WRAINB",
                "actionCode": "ISSUE",
                "issueTime": "2026-05-16T08:00:00Z",
            }
        }

    async def get_warning_info(self):
        return {"details": [{"warningStatementCode": "WRAIN", "subtype": "WRAINB", "contents": ["Heavy rain."]}]}

    async def get_current_weather_report(self):
        return {"updateTime": "2026-05-16T08:00:00Z", "warningMessage": ["Black rainstorm warning in force."]}

    async def get_local_weather_forecast(self):
        return {
            "generalSituation": "Showery with thunderstorms.",
            "forecastDesc": "Heavy showers at times.",
            "outlook": "Unsettled",
            "updateTime": "2026-05-16T08:00:00Z",
        }

    async def get_nine_day_forecast(self):
        return {"weatherForecast": [{"PSR": "High", "forecastWind": "Southwesterly"}]}

    async def get_lightning_count(self):
        return {"fields": ["district", "count"], "data": [["Tuen Mun", "3"]]}


class FakeLLM:
    def __init__(self, *args, **kwargs):
        pass

    async def run_structured(self, *, name, instructions, payload, output_type, model, temperature=0.1):
        del instructions, model, temperature
        if output_type is AgentAssessment:
            if name == "WarningAgent":
                return AgentAssessment(
                    risk_score=7.5,
                    district_scores={"Tuen Mun": 7.5},
                    confidence=0.9,
                    affected_districts=["Tuen Mun"],
                    primary_driver="WRAINB",
                    flags=["OFFICIAL_WARNING"],
                    reasoning="Official warning precedence.",
                    raw_extracts={},
                )
            return AgentAssessment(
                risk_score=2.0,
                district_scores={"Tuen Mun": 2.0},
                confidence=0.8,
                affected_districts=["Tuen Mun"],
                primary_driver=name,
                flags=[],
                reasoning=f"{name} baseline.",
                raw_extracts={},
            )
        if output_type is CompoundAssessment:
            return CompoundAssessment(flags=[])
        if output_type is SynthesisAssessment:
            max_signal = max(payload["signals"], key=lambda item: item["risk_score"])
            return SynthesisAssessment(
                alert_level=AlertLevel.RED,
                overall_risk_score=max_signal["risk_score"],
                district_scores={
                    "Tuen Mun": DistrictScore(
                        score=max_signal["risk_score"],
                        confidence="HIGH",
                        primary_driver=max_signal["agent_id"],
                    )
                },
                compound_flags=[],
                top_risk_districts=["Tuen Mun"],
                narrative_en="Official warnings indicate a high flood risk.",
                narrative_tc="官方警告顯示高水浸風險。",
                recommended_actions=[
                    RecommendedAction(code="EMERGENCY_RESPONSE", description="Escalate response.")
                ],
                confidence_overall=0.85,
                data_freshness=datetime(2026, 5, 16, 8, 0, tzinfo=UTC),
                reasoning="Use maximum warning-led signal.",
                next_update_priority=UpdatePriority.URGENT,
            )
        raise AssertionError(f"Unexpected output type: {output_type}")


@pytest.mark.asyncio
async def test_orchestrator_preserves_warning_precedence():
    orchestrator = FloodSwarmOrchestrator(
        settings=get_settings(),
        hko_client=FakeHKOClient(),
        llm=FakeLLM(),
    )
    output = await orchestrator.run()
    assert output.alert_level == AlertLevel.RED
    assert output.overall_risk_score == 7.5
    assert output.district_scores["Tuen Mun"].primary_driver == "WarningAgent"


@pytest.mark.asyncio
async def test_orchestrator_uses_stale_cache_on_agent_failure():
    class FlakyClient(FakeHKOClient):
        async def get_lightning_count(self):
            raise RuntimeError("temporary failure")

    orchestrator = FloodSwarmOrchestrator(
        settings=get_settings(),
        hko_client=FakeHKOClient(),
        llm=FakeLLM(),
    )
    await orchestrator.run()
    orchestrator.hko_client = FlakyClient()
    orchestrator._agents = orchestrator._build_agents()
    output = await orchestrator.run()
    stale_agents = {signal.agent_id for signal in output.agent_signals if signal.is_stale}
    assert "LightningAgent" in stale_agents
