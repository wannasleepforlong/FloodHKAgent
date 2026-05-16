from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any

from app.agents.base import AgentRunArtifacts, BaseFloodAgent
from app.config.data import TIDE_GAUGES
from app.models.schemas import AgentAssessment, AgentSignal, PeerQuery, PeerResponse, QueryType
from app.services.utils import all_district_scores, clamp_score, parse_iso8601, safe_float, utc_now


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
            hhot_table = station_data.get("hhot", {})
            hlt_table = station_data.get("hlt", {})
            gauge_meta = TIDE_GAUGES[station]

            latest_height = self._extract_latest_height(hhot_table)
            next_peak = self._extract_next_peak(hlt_table)
            latest_freshness = min(
                latest_freshness,
                parse_iso8601(hhot_table.get("updateTime") or data.get("as_of")),
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
                "latest_height_m": self._extract_latest_height(station_data.get("hhot", {})),
                "next_peak": self._extract_next_peak(station_data.get("hlt", {})),
            }
        return PeerResponse(
            from_agent=self.agent_id,
            data=summaries,
            confidence=0.85,
            latency_ms=0,
        )

    @staticmethod
    def _extract_latest_height(
        table: dict[str, Any], now: datetime | None = None
    ) -> float | None:
        rows = table.get("data", [])
        if not rows:
            return None

        current = now or utc_now()
        for row in reversed(rows):
            row_month = TideAgent._parse_int(row[0] if len(row) > 0 else None)
            row_day = TideAgent._parse_int(row[1] if len(row) > 1 else None)
            if row_month is None or row_day is None:
                continue

            if (row_month, row_day) > (current.month, current.day):
                continue

            latest_hour = current.hour if (row_month, row_day) == (current.month, current.day) else 24
            for hour in range(latest_hour, 0, -1):
                column_index = hour + 1
                if column_index >= len(row):
                    continue
                height = safe_float(row[column_index])
                if height is not None:
                    return height
        return None

    @staticmethod
    def _extract_next_peak(
        table: dict[str, Any], now: datetime | None = None
    ) -> dict[str, Any] | None:
        rows = table.get("data", [])
        if not rows:
            return None

        current = now or utc_now()
        candidates: list[tuple[datetime, dict[str, Any]]] = []
        for row in rows:
            row_month = TideAgent._parse_int(row[0] if len(row) > 0 else None)
            row_day = TideAgent._parse_int(row[1] if len(row) > 1 else None)
            if row_month is None or row_day is None:
                continue

            for offset in range(2, len(row), 3):
                if offset + 2 >= len(row):
                    continue
                time_str = row[offset]
                if not isinstance(time_str, str) or not time_str.strip():
                    continue

                try:
                    hour_str, minute_str = time_str.split(":", maxsplit=1)
                    event_time = current.replace(
                        month=row_month,
                        day=row_day,
                        hour=int(hour_str),
                        minute=int(minute_str),
                        second=0,
                        microsecond=0,
                    )
                except ValueError:
                    continue

                if event_time < current:
                    continue

                event_type = str(row[offset + 2]).strip().upper()
                if event_type != "H":
                    continue

                candidates.append(
                    (
                        event_time,
                        {
                            "month": row_month,
                            "date": row_day,
                            "time": time_str,
                            "height_m": safe_float(row[offset + 1]),
                            "type": event_type,
                        },
                    )
                )
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        event_time, row = candidates[0]
        return {"time": event_time.isoformat(), "raw": row}

    @staticmethod
    def _parse_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
