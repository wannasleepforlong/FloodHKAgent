from __future__ import annotations

from time import perf_counter
from typing import Any

from app.agents.base import AgentRunArtifacts, BaseFloodAgent
from app.config.data import FLOOD_RELEVANT_WARNING_CODES
from app.models.schemas import AgentAssessment, AgentSignal, PeerQuery, PeerResponse, QueryType
from app.services.utils import all_district_scores, parse_iso8601


class WarningAgent(BaseFloodAgent):
    agent_id = "WarningAgent"
    prompt_file = "warning_system.txt"
    settings_model_field = "warning_model"
    data_source = "weather.php?dataType=warnsum,warningInfo,rhrread"

    async def _fetch(self) -> Any:
        warnsum, warning_info, current = await self.deps.hko_client.get_warning_summary(), await self.deps.hko_client.get_warning_info(), await self.deps.hko_client.get_current_weather_report()
        return {"warnsum": warnsum, "warning_info": warning_info, "current": current}

    async def analyze(self, data: Any, peer_context: PeerResponse | None = None) -> AgentSignal:
        started_at = perf_counter()
        artifacts = AgentRunArtifacts()
        active_warnings: list[dict[str, Any]] = []
        district_scores = all_district_scores()
        data_freshness = parse_iso8601(data.get("current", {}).get("updateTime"))

        for warning_type, warning_obj in data.get("warnsum", {}).items():
            if not isinstance(warning_obj, dict):
                continue
            code = warning_obj.get("code")
            if code not in FLOOD_RELEVANT_WARNING_CODES:
                continue
            active_warnings.append(
                {
                    "warning_type": warning_type,
                    "name": warning_obj.get("name"),
                    "code": code,
                    "action_code": warning_obj.get("actionCode"),
                    "issue_time": warning_obj.get("issueTime"),
                }
            )
            if code == "WRAINB":
                for district in district_scores:
                    district_scores[district] = max(district_scores[district], 7.0)
            elif code in {"WRAINR", "WFNTSA", "TC8NE", "TC8SE", "TC8NW", "TC8SW", "TC9", "TC10"}:
                for district in district_scores:
                    district_scores[district] = max(district_scores[district], 5.5)

        warning_details = data.get("warning_info", {}).get("details", [])
        if any(item.get("code") == "WFNTSA" or item.get("warning_type") == "WFNTSA" for item in active_warnings) and peer_context is None:
            peer_context = await self.issue_peer_query(
                PeerQuery(
                    from_agent=self.agent_id,
                    to_agent="RainfallAgent",
                    query_type=QueryType.RAINFALL_CORROBORATION,
                    context="Corroborate flood-related NT rainfall exceedances from hourly rainfall data.",
                    urgency="HIGH",
                ),
                artifacts,
            )

        payload = {
            "active_warnings": active_warnings,
            "warning_details": warning_details,
            "warning_messages": data.get("current", {}).get("warningMessage", []),
            "rainstorm_reminder": data.get("current", {}).get("rainstormReminder"),
            "peer_context": peer_context.model_dump(mode="json") if peer_context else None,
            "district_baseline_scores": district_scores,
        }
        assessment = await self.run_llm_assessment(payload=payload, output_type=AgentAssessment)
        return self.build_signal(
            assessment=assessment,
            data_freshness=data_freshness,
            artifacts=artifacts,
            started_at=started_at,
        )
