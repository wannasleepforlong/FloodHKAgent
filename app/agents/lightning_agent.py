from __future__ import annotations

from time import perf_counter
from typing import Any

from app.agents.base import AgentRunArtifacts, BaseFloodAgent
from app.models.schemas import AgentAssessment, AgentSignal, PeerQuery, PeerResponse, QueryType
from app.services.utils import all_district_scores, safe_float, utc_now


def lightning_table_to_dicts(table: dict[str, Any]) -> list[dict[str, Any]]:
    fields = table.get("fields", [])
    return [dict(zip(fields, row)) for row in table.get("data", [])]


class LightningAgent(BaseFloodAgent):
    agent_id = "LightningAgent"
    prompt_file = "lightning_system.txt"
    settings_model_field = "lightning_model"
    data_source = "opendata.php?dataType=LHL"

    async def _fetch(self) -> Any:
        return await self.deps.hko_client.get_lightning_count()

    async def analyze(self, data: Any, peer_context: PeerResponse | None = None) -> AgentSignal:
        started_at = perf_counter()
        artifacts = AgentRunArtifacts()
        rows = lightning_table_to_dicts(data)
        district_scores = all_district_scores()
        district_counts: list[dict[str, Any]] = []
        max_count = 0.0

        for row in rows:
            count = None
            district = None
            for key, value in row.items():
                if district is None and "district" in key.lower():
                    district = str(value)
                if count is None:
                    count = safe_float(value)
            if district is None or count is None:
                continue
            district_scores[district] = max(district_scores.get(district, 0.0), min(10.0, count / 12))
            district_counts.append({"district": district, "count": count})
            max_count = max(max_count, count)

        if max_count >= 20 and peer_context is None:
            peer_context = await self.issue_peer_query(
                PeerQuery(
                    from_agent=self.agent_id,
                    to_agent="ForecastAgent",
                    query_type=QueryType.WIND_DIRECTION,
                    context="Provide current forecast wind direction and near-term steering clues for lightning cell movement.",
                    urgency="LOW",
                ),
                artifacts,
            )

        payload = {
            "district_counts": district_counts,
            "district_baseline_scores": district_scores,
            "peer_context": peer_context.model_dump(mode="json") if peer_context else None,
        }
        assessment = await self.run_llm_assessment(payload=payload, output_type=AgentAssessment)
        confidence_penalty = 0.1 if max_count >= 20 and peer_context is None else 0.0
        return self.build_signal(
            assessment=assessment,
            data_freshness=utc_now(),
            artifacts=artifacts,
            started_at=started_at,
            confidence_penalty=confidence_penalty,
        )
