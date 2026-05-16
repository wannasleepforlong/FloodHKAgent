from __future__ import annotations

from time import perf_counter
from typing import Any

from app.agents.base import AgentRunArtifacts, BaseFloodAgent
from app.config.data import DISTRICT_STATION_MAP, RAIN_THRESHOLDS_MM
from app.models.schemas import AgentAssessment, AgentSignal, PeerQuery, PeerResponse, QueryType
from app.services.utils import all_district_scores, clamp_score, parse_iso8601, safe_float


class RainfallAgent(BaseFloodAgent):
    agent_id = "RainfallAgent"
    prompt_file = "rainfall_system.txt"
    settings_model_field = "rainfall_model"
    data_source = "hourlyRainfall.php"

    async def _fetch(self) -> Any:
        return await self.deps.hko_client.get_hourly_rainfall()

    async def analyze(self, data: Any, peer_context: PeerResponse | None = None) -> AgentSignal:
        started_at = perf_counter()
        artifacts = AgentRunArtifacts()
        district_scores = all_district_scores()
        stations: list[dict[str, Any]] = []
        maintenance_count = 0
        max_rainfall = 0.0

        for row in data.get("hourlyRainfall", []):
            station_id = row.get("automaticWeatherStationID", "")
            rainfall = safe_float(row.get("value"))
            if rainfall is None:
                maintenance_count += 1
                rainfall_for_summary = "M"
            else:
                rainfall_for_summary = rainfall
                max_rainfall = max(max_rainfall, rainfall)
            districts = [
                district
                for district, station_ids in DISTRICT_STATION_MAP.items()
                if station_id in station_ids
            ]
            for district in districts:
                if rainfall is not None:
                    district_scores[district] = clamp_score(max(district_scores[district], rainfall / 10))
            stations.append(
                {
                    "station_name": row.get("automaticWeatherStation"),
                    "station_id": station_id,
                    "value_mm": rainfall_for_summary,
                    "districts": districts,
                }
            )

        confidence_penalty = 0.15 if maintenance_count > 3 else 0.0

        if max_rainfall >= RAIN_THRESHOLDS_MM["black"] and peer_context is None:
            peer_context = await self.issue_peer_query(
                PeerQuery(
                    from_agent=self.agent_id,
                    to_agent="TideAgent",
                    query_type=QueryType.TIDE_TIMING,
                    context="Provide current tide state and time to next high tide for flood compounding.",
                    urgency="HIGH",
                ),
                artifacts,
            )
            if peer_context is None:
                confidence_penalty += 0.1

        payload = {
            "thresholds_mm": RAIN_THRESHOLDS_MM,
            "obs_time": data.get("obsTime"),
            "stations": stations,
            "district_baseline_scores": district_scores,
            "maintenance_count": maintenance_count,
            "peer_context": peer_context.model_dump(mode="json") if peer_context else None,
        }
        assessment = await self.run_llm_assessment(payload=payload, output_type=AgentAssessment)
        return self.build_signal(
            assessment=assessment,
            data_freshness=parse_iso8601(data.get("obsTime")),
            artifacts=artifacts,
            started_at=started_at,
            confidence_penalty=confidence_penalty,
        )

    def can_answer_peer_query(self, query: PeerQuery) -> bool:
        return query.query_type == QueryType.RAINFALL_CORROBORATION

    async def handle_peer_query(self, query: PeerQuery) -> PeerResponse:
        rows = self._last_payload.get("hourlyRainfall", []) if self._last_payload else []
        corroboration: list[dict[str, Any]] = []
        for row in rows:
            rainfall = safe_float(row.get("value"))
            if rainfall is not None and rainfall >= RAIN_THRESHOLDS_MM["red"]:
                corroboration.append(
                    {
                        "station_id": row.get("automaticWeatherStationID"),
                        "station_name": row.get("automaticWeatherStation"),
                        "value_mm": rainfall,
                    }
                )
        return PeerResponse(
            from_agent=self.agent_id,
            data={"high_rainfall_stations": corroboration[:10]},
            confidence=0.9 if corroboration else 0.5,
            latency_ms=0,
        )
