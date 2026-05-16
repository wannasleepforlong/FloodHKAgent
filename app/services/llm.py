from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

from app.settings import Settings

try:
    from agents import (
        Agent,
        AgentOutputSchema,
        AsyncOpenAI,
        ModelSettings,
        OpenAIChatCompletionsModel,
        RunConfig,
        Runner,
        set_tracing_disabled,
    )
except ImportError as exc:  # pragma: no cover - exercised only when deps are missing
    Agent = AgentOutputSchema = AsyncOpenAI = ModelSettings = OpenAIChatCompletionsModel = RunConfig = Runner = None
    set_tracing_disabled = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

T = TypeVar("T", bound=BaseModel)


class LLMRuntime:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        if IMPORT_ERROR is None:
            self._configure_provider()

    def _configure_provider(self) -> None:
        if self.settings.llm_disable_tracing and set_tracing_disabled is not None:
            set_tracing_disabled(disabled=True)

        if self.settings.llm_api_type == "chat_completions":
            extra_headers: dict[str, str] = {}
            if self.settings.llm_provider == "openrouter":
                if self.settings.llm_site_url:
                    extra_headers["HTTP-Referer"] = self.settings.llm_site_url
                if self.settings.llm_app_name:
                    extra_headers["X-Title"] = self.settings.llm_app_name

            client_kwargs: dict[str, Any] = {}
            if self.settings.llm_api_key:
                client_kwargs["api_key"] = self.settings.llm_api_key
            if self.settings.llm_base_url:
                client_kwargs["base_url"] = self.settings.llm_base_url
            if extra_headers:
                client_kwargs["default_headers"] = extra_headers
            self._client = AsyncOpenAI(**client_kwargs)

    def _resolve_model(self, model: str) -> tuple[Any, RunConfig | None]:
        if self.settings.llm_api_type == "chat_completions":
            if self._client is None:
                raise RuntimeError(
                    "Chat Completions provider selected, but no compatible client could be created. "
                    "Set FLOOD_SWARM_LLM_API_KEY and FLOOD_SWARM_LLM_BASE_URL, or use a supported provider preset."
                )
            return (
                OpenAIChatCompletionsModel(model=model, openai_client=self._client),
                None,
            )
        return model, RunConfig(model=model)

    async def run_structured(
        self,
        *,
        name: str,
        instructions: str,
        payload: dict[str, Any],
        output_type: type[T],
        model: str,
        temperature: float = 0.1,
    ) -> T:
        if IMPORT_ERROR is not None:
            raise RuntimeError(
                "openai-agents is not installed. Install project dependencies before running the swarm."
            ) from IMPORT_ERROR

        payload_text = json.dumps(payload, ensure_ascii=False, default=str, indent=2)
        user_prompt = f"Analyze the following JSON payload and return only the structured output.\n{payload_text}"
        last_error: Exception | None = None

        for attempt in range(2):
            agent_model, run_config = self._resolve_model(model)
            agent = Agent(
                name=name,
                instructions=instructions,
                output_type=AgentOutputSchema(output_type, strict_json_schema=False),
                model=agent_model,
                model_settings=ModelSettings(temperature=temperature),
            )
            try:
                result = await Runner.run(
                    agent,
                    user_prompt,
                    run_config=run_config,
                )
                output = result.final_output
                if not isinstance(output, output_type):
                    raise TypeError(
                        f"Expected {output_type.__name__}, got {type(output).__name__}"
                    )
                return output
            except Exception as exc:  # pragma: no cover - depends on SDK/runtime
                last_error = exc
                if attempt == 0:
                    user_prompt = (
                        "Your previous response failed validation. "
                        f"Retry and strictly match the target schema.\nError: {exc}\n{payload_text}"
                    )
                    continue
                raise

        assert last_error is not None
        raise last_error
