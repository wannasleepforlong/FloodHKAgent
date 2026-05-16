from __future__ import annotations

from time import perf_counter
from typing import Any

from app.agents.base import AgentRunArtifacts, BaseFloodAgent
from app.models.schemas import AgentAssessment, AgentSignal, PeerQuery, PeerResponse, QueryType
from app.services.utils import all_district_scores, parse_iso8601


class ForecastAgent(BaseFloodAgent):
    agent_id = "ForecastAgent"
    prompt_file = "forecast_system.txt"
    settings_model_field = "forecast_model"
    data_source = "weather.php?dataType=flw,fnd"

    async def _fetch(self) -> Any:
        flw, fnd = await self.deps.hko_client.get_local_weather_forecast(), await self.deps.hko_client.get_nine_day_forecast()
        return {"flw": flw, "fnd": fnd}

    async def analyze(self, data: Any, peer_context: PeerResponse | None = None) -> AgentSignal:
        del peer_context
        started_at = perf_counter()
        artifacts = AgentRunArtifacts()
        weather_forecast = data.get("fnd", {}).get("weatherForecast", [])
        psr_values = [
            item.get("PSR")
            for item in weather_forecast[:3]
            if isinstance(item, dict) and item.get("PSR") is not None
        ]
        payload = {
            "general_situation": data.get("flw", {}).get("generalSituation"),
            "forecast_desc": data.get("flw", {}).get("forecastDesc"),
            "outlook": data.get("flw", {}).get("outlook"),
            "tropical_cyclone_info": data.get("flw", {}).get("tclnfo"),
            "next_three_days": weather_forecast[:3],
            "psr_values": psr_values,
            "district_baseline_scores": all_district_scores(1.5 if psr_values else 0.5),
        }
        assessment = await self.run_llm_assessment(payload=payload, output_type=AgentAssessment)
        return self.build_signal(
            assessment=assessment,
            data_freshness=parse_iso8601(data.get("flw", {}).get("updateTime")),
            artifacts=artifacts,
            started_at=started_at,
        )

    def can_answer_peer_query(self, query: PeerQuery) -> bool:
        return query.query_type == QueryType.WIND_DIRECTION

    async def handle_peer_query(self, query: PeerQuery) -> PeerResponse:
        del query
        flw = self._last_payload.get("flw", {}) if self._last_payload else {}
        fnd = self._last_payload.get("fnd", {}) if self._last_payload else {}
        next_day = (fnd.get("weatherForecast") or [{}])[0]
        return PeerResponse(
            from_agent=self.agent_id,
            data={
                "forecast_wind": next_day.get("forecastWind"),
                "forecast_weather": next_day.get("forecastWeather"),
                "general_situation": flw.get("generalSituation"),
            },
            confidence=0.8,
            latency_ms=0,
        )
