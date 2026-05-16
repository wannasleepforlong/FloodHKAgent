from __future__ import annotations

from app.models.schemas import AgentSignal, CompoundFlag, SynthesisAssessment
from app.prompts.loader import load_prompt
from app.services.llm import LLMRuntime
from app.settings import Settings


class SynthesisAgent:
    def __init__(self, llm: LLMRuntime, settings: Settings):
        self.llm = llm
        self.settings = settings
        self.instructions = load_prompt("synthesis_system.txt")

    async def analyze(
        self,
        *,
        signals: list[AgentSignal],
        compound_flags: list[CompoundFlag],
        month: int,
        season: str,
    ) -> SynthesisAssessment:
        payload = {
            "signals": [signal.model_dump(mode="json") for signal in signals],
            "compound_flags": [flag.model_dump(mode="json") for flag in compound_flags],
            "month": month,
            "season": season,
        }
        return await self.llm.run_structured(
            name="SynthesisAgent",
            instructions=self.instructions,
            payload=payload,
            output_type=SynthesisAssessment,
            model=self.settings.synthesis_model,
        )
