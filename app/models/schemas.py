from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class AlertLevel(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    AMBER = "AMBER"
    RED = "RED"
    BLACK = "BLACK"


class UpdatePriority(str, Enum):
    ROUTINE = "ROUTINE"
    ELEVATED = "ELEVATED"
    URGENT = "URGENT"


class QueryType(str, Enum):
    TIDE_TIMING = "TIDE_TIMING"
    RAINFALL_CORROBORATION = "RAINFALL_CORROBORATION"
    WIND_DIRECTION = "WIND_DIRECTION"
    FORECAST_DURATION = "FORECAST_DURATION"


class QueryUrgency(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class RunMode(str, Enum):
    LIVE = "live"
    FIXTURE = "fixture"


class PeerQuery(StrictModel):
    from_agent: str
    to_agent: str
    query_type: QueryType
    context: str
    urgency: QueryUrgency = QueryUrgency.LOW


class PeerResponse(StrictModel):
    from_agent: str
    data: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: int = Field(ge=0)


class AgentAssessment(StrictModel):
    risk_score: float = Field(ge=0, le=10)
    district_scores: dict[str, float]
    confidence: float = Field(ge=0.0, le=1.0)
    affected_districts: list[str]
    primary_driver: str
    flags: list[str] = Field(default_factory=list)
    reasoning: str
    raw_extracts: dict[str, Any] = Field(default_factory=dict)


class AgentSignal(StrictModel):
    agent_id: str
    version: str = "1.0"
    timestamp: datetime
    data_source: str
    data_freshness: datetime
    risk_score: float = Field(ge=0, le=10)
    district_scores: dict[str, float]
    confidence: float = Field(ge=0.0, le=1.0)
    affected_districts: list[str]
    primary_driver: str
    flags: list[str] = Field(default_factory=list)
    reasoning: str
    raw_extracts: dict[str, Any] = Field(default_factory=dict)
    peer_queries_issued: list[PeerQuery] = Field(default_factory=list)
    peer_responses_received: list[PeerResponse] = Field(default_factory=list)
    latency_ms: int = Field(ge=0)
    is_stale: bool = False
    prompt_version: str = "v1"


class CompoundFlag(StrictModel):
    flag: str
    severity: int = Field(ge=1, le=3)
    affected_districts: list[str]
    reasoning: str


class CompoundAssessment(StrictModel):
    flags: list[CompoundFlag]


class DistrictScore(StrictModel):
    score: float = Field(ge=0, le=10)
    confidence: str
    primary_driver: str


class RecommendedAction(StrictModel):
    code: str
    description: str


class SynthesisAssessment(StrictModel):
    alert_level: AlertLevel
    overall_risk_score: float = Field(ge=0, le=10)
    district_scores: dict[str, DistrictScore]
    compound_flags: list[CompoundFlag]
    top_risk_districts: list[str]
    narrative_en: str
    narrative_tc: str
    recommended_actions: list[RecommendedAction]
    confidence_overall: float = Field(ge=0.0, le=1.0)
    data_freshness: datetime
    reasoning: str
    next_update_priority: UpdatePriority


class SystemHealth(StrictModel):
    agents_healthy: int = Field(ge=0)
    stale_signals: list[str] = Field(default_factory=list)
    degraded_confidence: bool = False


class FloodAlertOutput(StrictModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime
    alert_level: AlertLevel
    overall_risk_score: float = Field(ge=0, le=10)
    district_scores: dict[str, DistrictScore]
    compound_flags: list[CompoundFlag]
    top_risk_districts: list[str]
    narrative_en: str
    narrative_tc: str
    recommended_actions: list[RecommendedAction]
    confidence_overall: float = Field(ge=0.0, le=1.0)
    agent_signals: list[AgentSignal]
    compound_detector_output: list[CompoundFlag]
    data_freshness: datetime
    reasoning: str
    next_update_priority: UpdatePriority
    system_health: SystemHealth


class RunAlertRequest(StrictModel):
    mode: RunMode = RunMode.LIVE


class RunMetadata(StrictModel):
    started_at: datetime
    finished_at: datetime
    run_id: str


    @model_validator(mode="after")
    def validate_times(self) -> "RunMetadata":
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must be after started_at")
        return self
