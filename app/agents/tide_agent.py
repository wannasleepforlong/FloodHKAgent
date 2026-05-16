from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any

from app.agents.base import AgentRunArtifacts, BaseFloodAgent
from app.config.data import TIDE_GAUGES
from app.models.schemas import AgentAssessment, AgentSignal, PeerQuery, PeerResponse, QueryType
from app.services.utils import all_district_scores, clamp_score, parse_iso8601, safe_float, utc_now


def table_to_dicts(table: dict[str, Any]) -> list[dict[str, Any]]:
    fields = table.get("fields", [])
    return [dict(zip(fields, row)) for row in table.get("data", [])]


class TideAgent(BaseFloodAgent):
    agent_id = "TideAgent"
    prompt_file = "tide_system.txt"
    settings_model_field = "tide_model"
    data_source = "opendata.php?dataType=HHOT,HLT"

    async def _fetch(self) -> Any:
        return await self.deps.hko_client.get_tide_bundle(utc_now())

    async def analyze(self, data: Any, peer_context: PeerResponse | None = None) -> AgentSignal:
        del peer_context
        started_at = perf_counter()
        artifacts = AgentRunArtifacts()
        district_scores = all_district_scores()
        station_summaries: dict[str, Any] = {}
        latest_freshness = utc_now()

        for station, station_data in data.get("stations", {}).items():
            hhot_rows = table_to_dicts(station_data.get("hhot", {}))
            hlt_rows = table_to_dicts(station_data.get("hlt", {}))
            gauge_meta = TIDE_GAUGES[station]

            latest_height = self._extract_latest_height(hhot_rows)
            next_peak = self._extract_next_peak(hlt_rows)
            latest_freshness = min(
                latest_freshness,
                parse_iso8601(station_data.get("hhot", {}).get("updateTime") or data.get("as_of")),
            )

            station_summaries[station] = {
                "station_name": gauge_meta["station_name"],
                "latest_height_m": latest_height,
                "danger_zone_m": gauge_meta["danger_zone"],
                "districts": gauge_meta["districts"],
                "next_peak": next_peak,
            }
            if latest_height is not None:
                danger_excess = max(0.0, latest_height - gauge_meta["danger_zone"])
                for district in gauge_meta["districts"]:
                    district_scores[district] = clamp_score(
                        max(district_scores[district], 4 + danger_excess * 10)
                    )

        payload = {
            "stations": station_summaries,
            "district_baseline_scores": district_scores,
        }
        assessment = await self.run_llm_assessment(payload=payload, output_type=AgentAssessment)
        return self.build_signal(
            assessment=assessment,
            data_freshness=latest_freshness,
            artifacts=artifacts,
            started_at=started_at,
        )

    def can_answer_peer_query(self, query: PeerQuery) -> bool:
        return query.query_type == QueryType.TIDE_TIMING

    async def handle_peer_query(self, query: PeerQuery) -> PeerResponse:
        del query
        summaries: dict[str, Any] = {}
        for station, station_data in self._last_payload.get("stations", {}).items():
            summaries[station] = {
                "latest_height_m": self._extract_latest_height(
                    table_to_dicts(station_data.get("hhot", {}))
                ),
                "next_peak": self._extract_next_peak(table_to_dicts(station_data.get("hlt", {}))),
            }
        return PeerResponse(
            from_agent=self.agent_id,
            data=summaries,
            confidence=0.85,
            latency_ms=0,
        )

    @staticmethod
    def _extract_latest_height(rows: list[dict[str, Any]]) -> float | None:
        if not rows:
            return None
        latest = rows[-1]
        for key, value in latest.items():
            if "height" in key.lower():
                return safe_float(value)
        for value in latest.values():
            height = safe_float(value)
            if height is not None:
                return height
        return None

    @staticmethod
    def _extract_next_peak(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not rows:
            return None
        now = utc_now()
        candidates: list[tuple[datetime, dict[str, Any]]] = []
        for row in rows:
            parsed_time = None
            for value in row.values():
                if isinstance(value, str):
                    try:
                        parsed_time = parse_iso8601(value)
                        break
                    except ValueError:
                        continue
            if parsed_time is None or parsed_time < now:
                continue
            candidates.append((parsed_time, row))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        event_time, row = candidates[0]
        return {"time": event_time.isoformat(), "raw": row}
