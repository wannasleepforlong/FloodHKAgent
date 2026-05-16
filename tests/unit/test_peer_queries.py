import asyncio
from datetime import UTC, datetime

import pytest

from app.agents.base import AgentDependencies, AgentRunArtifacts, BaseFloodAgent
from app.models.schemas import AgentAssessment, AgentSignal, PeerQuery, QueryType
from app.services.llm import LLMRuntime
from app.settings import get_settings


class DummyAgent(BaseFloodAgent):
    agent_id = "DummyAgent"
    prompt_file = "rainfall_system.txt"
    settings_model_field = "rainfall_model"
    data_source = "dummy"

    async def _fetch(self):
        return {}

    async def analyze(self, data, peer_context=None) -> AgentSignal:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_peer_query_timeout_returns_none():
    settings = get_settings()

    async def slow_handler(query):
        await asyncio.sleep(settings.peer_query_timeout_seconds + 0.1)
        return None

    deps = AgentDependencies(
        settings=settings,
        hko_client=None,  # type: ignore[arg-type]
        llm=LLMRuntime(settings),
        peer_query_handler=slow_handler,
    )
    agent = DummyAgent(deps)
    result = await agent.issue_peer_query(
        PeerQuery(
            from_agent="DummyAgent",
            to_agent="OtherAgent",
            query_type=QueryType.TIDE_TIMING,
            context="test",
            urgency="HIGH",
        ),
        AgentRunArtifacts(),
    )
    assert result is None
