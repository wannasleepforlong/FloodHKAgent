from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Awaitable, Callable

from app.api.hko_client import HKOClient
from app.models.schemas import AgentAssessment, AgentSignal, PeerQuery, PeerResponse
from app.prompts.loader import load_prompt
from app.services.llm import LLMRuntime
from app.services.utils import utc_now
from app.settings import Settings

PeerQueryHandler = Callable[[PeerQuery], Awaitable[PeerResponse | None]]


@dataclass
class AgentDependencies:
    settings: Settings
    hko_client: HKOClient
    llm: LLMRuntime
    peer_query_handler: PeerQueryHandler | None = None


@dataclass
class AgentRunArtifacts:
    peer_queries: list[PeerQuery] = field(default_factory=list)
    peer_responses: list[PeerResponse] = field(default_factory=list)


class BaseFloodAgent(ABC):
    agent_id: str
    prompt_file: str
    model_name: str
    settings_model_field: str
    data_source: str
    prompt_version: str = "v1"

    def __init__(self, deps: AgentDependencies):
        self.deps = deps
        self.model_name = getattr(deps.settings, self.settings_model_field)
        self._last_payload: Any = None
        self._last_signal: AgentSignal | None = None

    @property
    def instructions(self) -> str:
        return load_prompt(self.prompt_file)

    async def fetch(self) -> Any:
        payload = await self._fetch()
        self._last_payload = payload
        return payload

    @abstractmethod
    async def _fetch(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def analyze(self, data: Any, peer_context: PeerResponse | None = None) -> AgentSignal:
        raise NotImplementedError

    def can_answer_peer_query(self, query: PeerQuery) -> bool:
        return False

    async def handle_peer_query(self, query: PeerQuery) -> PeerResponse:
        raise ValueError(f"{self.agent_id} cannot answer query type {query.query_type}")

    async def issue_peer_query(
        self, query: PeerQuery, artifacts: AgentRunArtifacts
    ) -> PeerResponse | None:
        if self.deps.peer_query_handler is None:
            return None
        artifacts.peer_queries.append(query)
        try:
            response = await asyncio.wait_for(
                self.deps.peer_query_handler(query),
                timeout=self.deps.settings.peer_query_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return None
        if response is not None:
            artifacts.peer_responses.append(response)
        return response

    async def run_llm_assessment(
        self, *, payload: dict[str, Any], output_type: type[AgentAssessment]
    ) -> AgentAssessment:
        return await self.deps.llm.run_structured(
            name=self.agent_id,
            instructions=self.instructions,
            payload=payload,
            output_type=output_type,
            model=self.model_name,
        )

    def build_signal(
        self,
        *,
        assessment: AgentAssessment,
        data_freshness,
        artifacts: AgentRunArtifacts,
        started_at: float,
        confidence_penalty: float = 0.0,
    ) -> AgentSignal:
        signal = AgentSignal(
            agent_id=self.agent_id,
            timestamp=utc_now(),
            data_source=self.data_source,
            data_freshness=data_freshness,
            risk_score=assessment.risk_score,
            district_scores=assessment.district_scores,
            confidence=max(0.0, round(assessment.confidence - confidence_penalty, 3)),
            affected_districts=assessment.affected_districts,
            primary_driver=assessment.primary_driver,
            flags=assessment.flags,
            reasoning=assessment.reasoning,
            raw_extracts=assessment.raw_extracts,
            peer_queries_issued=artifacts.peer_queries,
            peer_responses_received=artifacts.peer_responses,
            latency_ms=int((perf_counter() - started_at) * 1000),
            prompt_version=self.prompt_version,
        )
        self._last_signal = signal
        return signal
