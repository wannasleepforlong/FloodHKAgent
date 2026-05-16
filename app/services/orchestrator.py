from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base import AgentDependencies, BaseFloodAgent
from app.agents.compound_detector import CompoundDetector
from app.agents.forecast_agent import ForecastAgent
from app.agents.lightning_agent import LightningAgent
from app.agents.rainfall_agent import RainfallAgent
from app.agents.synthesis_agent import SynthesisAgent
from app.agents.tide_agent import TideAgent
from app.agents.warning_agent import WarningAgent
from app.api.hko_client import HKOClient
from app.config.data import COMPOUND_RULES
from app.models.schemas import (
    AgentSignal,
    CompoundFlag,
    FloodAlertOutput,
    PeerQuery,
    PeerResponse,
    RecommendedAction,
    RunMode,
    SynthesisAssessment,
    SystemHealth,
)
from app.services.llm import LLMRuntime
from app.services.logger import RunLogger
from app.services.utils import all_district_scores, season_for_month, utc_now
from app.settings import Settings


class FloodSwarmOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        hko_client: HKOClient | None = None,
        llm: LLMRuntime | None = None,
        logger: RunLogger | None = None,
    ):
        self.settings = settings
        self.hko_client = hko_client or HKOClient(settings)
        self.llm = llm or LLMRuntime(settings)
        self.logger = logger or RunLogger(settings.log_dir)
        self.signal_cache: dict[str, AgentSignal] = {}
        self._agents = self._build_agents()
        self._compound_detector = CompoundDetector(self.llm, settings)
        self._synthesis_agent = SynthesisAgent(self.llm, settings)

    def _build_agents(self) -> dict[str, BaseFloodAgent]:
        deps = AgentDependencies(
            settings=self.settings,
            hko_client=self.hko_client,
            llm=self.llm,
            peer_query_handler=self.route_peer_query,
        )
        agents: list[BaseFloodAgent] = [
            RainfallAgent(deps),
            TideAgent(deps),
            WarningAgent(deps),
            ForecastAgent(deps),
            LightningAgent(deps),
        ]
        return {agent.agent_id: agent for agent in agents}

    async def aclose(self) -> None:
        await self.hko_client.aclose()

    async def route_peer_query(self, query: PeerQuery) -> PeerResponse | None:
        target = self._agents.get(query.to_agent)
        if target is None or not target.can_answer_peer_query(query):
            return None
        return await target.handle_peer_query(query)

    async def run(self, mode: RunMode = RunMode.LIVE) -> FloodAlertOutput:
        if mode != RunMode.LIVE:
            raise ValueError("Only live mode is implemented in the MVP.")

        specialist_signals = await self._run_specialists()
        compound_flags = await self._compound_detector.analyze(specialist_signals)
        stale_signals = [signal.agent_id for signal in specialist_signals if signal.is_stale]
        degraded_confidence = len(stale_signals) > 2
        if degraded_confidence:
            compound_flags.append(
                CompoundFlag(
                    flag="DEGRADED_CONFIDENCE",
                    severity=2,
                    affected_districts=[],
                    reasoning=COMPOUND_RULES["DEGRADED_CONFIDENCE"],
                )
            )
        synthesis = await self._synthesis_agent.analyze(
            signals=specialist_signals,
            compound_flags=compound_flags,
            month=utc_now().month,
            season=season_for_month(utc_now().month),
        )
        output = self._build_output(
            synthesis=synthesis,
            specialist_signals=specialist_signals,
            compound_flags=compound_flags,
            stale_signals=stale_signals,
            degraded_confidence=degraded_confidence,
        )
        self.logger.write(output)
        return output

    async def _run_specialists(self) -> list[AgentSignal]:
        fetch_results = await asyncio.gather(
            *(self._fetch_with_retry(agent) for agent in self._agents.values())
        )
        analyze_tasks = [
            self._analyze_with_retry(agent, payload)
            for agent, payload in zip(self._agents.values(), fetch_results, strict=True)
        ]
        return list(await asyncio.gather(*analyze_tasks))

    async def _fetch_with_retry(self, agent: BaseFloodAgent) -> Any:
        try:
            return await asyncio.wait_for(agent.fetch(), timeout=self.settings.agent_timeout_seconds)
        except Exception as first_error:
            try:
                return await asyncio.wait_for(
                    agent.fetch(), timeout=self.settings.agent_retry_timeout_seconds
                )
            except Exception:
                return first_error

    async def _analyze_with_retry(self, agent: BaseFloodAgent, payload: Any) -> AgentSignal:
        if isinstance(payload, Exception):
            cached = self.signal_cache.get(agent.agent_id)
            if cached is not None:
                stale_signal = cached.model_copy(
                    update={
                        "timestamp": utc_now(),
                        "is_stale": True,
                        "flags": list(dict.fromkeys([*cached.flags, "STALE_SIGNAL"])),
                        "reasoning": f"{cached.reasoning} Upstream fetch failed; cached signal reused.",
                    }
                )
                self.signal_cache[agent.agent_id] = stale_signal
                return stale_signal
            return self._unknown_signal(agent)
        try:
            signal = await asyncio.wait_for(
                agent.analyze(payload), timeout=self.settings.agent_timeout_seconds
            )
        except Exception:
            try:
                signal = await asyncio.wait_for(
                    agent.analyze(payload), timeout=self.settings.agent_retry_timeout_seconds
                )
            except Exception:
                cached = self.signal_cache.get(agent.agent_id)
                if cached is not None:
                    stale_signal = cached.model_copy(
                        update={
                            "timestamp": utc_now(),
                            "is_stale": True,
                            "flags": list(dict.fromkeys([*cached.flags, "STALE_SIGNAL"])),
                        }
                    )
                    self.signal_cache[agent.agent_id] = stale_signal
                    return stale_signal
                signal = self._unknown_signal(agent)

        self.signal_cache[agent.agent_id] = signal
        return signal

    def _unknown_signal(self, agent: BaseFloodAgent) -> AgentSignal:
        return AgentSignal(
            agent_id=agent.agent_id,
            timestamp=utc_now(),
            data_source=agent.data_source,
            data_freshness=utc_now(),
            risk_score=1.0,
            district_scores=all_district_scores(0.0),
            confidence=0.1,
            affected_districts=[],
            primary_driver="UNKNOWN",
            flags=["UNKNOWN_SIGNAL"],
            reasoning="Agent failed without a cached fallback signal.",
            raw_extracts={},
            latency_ms=0,
            is_stale=True,
            prompt_version=agent.prompt_version,
        )

    def _build_output(
        self,
        *,
        synthesis: SynthesisAssessment,
        specialist_signals: list[AgentSignal],
        compound_flags: list[CompoundFlag],
        stale_signals: list[str],
        degraded_confidence: bool,
    ) -> FloodAlertOutput:
        return FloodAlertOutput(
            generated_at=utc_now(),
            alert_level=synthesis.alert_level,
            overall_risk_score=synthesis.overall_risk_score,
            district_scores=synthesis.district_scores,
            compound_flags=synthesis.compound_flags,
            top_risk_districts=synthesis.top_risk_districts,
            narrative_en=synthesis.narrative_en,
            narrative_tc=synthesis.narrative_tc,
            recommended_actions=synthesis.recommended_actions,
            confidence_overall=synthesis.confidence_overall,
            agent_signals=specialist_signals,
            compound_detector_output=compound_flags,
            data_freshness=synthesis.data_freshness,
            reasoning=synthesis.reasoning,
            next_update_priority=synthesis.next_update_priority,
            system_health=SystemHealth(
                agents_healthy=len([signal for signal in specialist_signals if not signal.is_stale]),
                stale_signals=stale_signals,
                degraded_confidence=degraded_confidence,
            ),
        )
