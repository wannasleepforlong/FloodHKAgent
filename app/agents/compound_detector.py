from __future__ import annotations

from app.models.schemas import AgentSignal, CompoundAssessment, CompoundFlag
from app.prompts.loader import load_prompt
from app.services.llm import LLMRuntime
from app.settings import Settings


class CompoundDetector:
    def __init__(self, llm: LLMRuntime, settings: Settings):
        self.llm = llm
        self.settings = settings
        self.instructions = load_prompt("compound_system.txt")

    async def analyze(self, signals: list[AgentSignal]) -> list[CompoundFlag]:
        payload = {
            "signals": [signal.model_dump(mode="json") for signal in signals],
        }
        assessment = await self.llm.run_structured(
            name="CompoundDetector",
            instructions=self.instructions,
            payload=payload,
            output_type=CompoundAssessment,
            model=self.settings.compound_model,
        )
        return assessment.flags
