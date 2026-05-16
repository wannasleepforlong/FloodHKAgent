from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


load_dotenv(find_dotenv(usecwd=True), override=False)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _provider_defaults(provider: str) -> tuple[str | None, str | None, str]:
    normalized = provider.strip().lower()
    if normalized == "openrouter":
        return (
            os.getenv("OPENROUTER_API_KEY"),
            "https://openrouter.ai/api/v1",
            "chat_completions",
        )
    if normalized == "mistral":
        return (
            os.getenv("MISTRAL_API_KEY"),
            "https://api.mistral.ai/v1",
            "chat_completions",
        )
    if normalized in {"custom", "openai_compatible"}:
        return (None, None, "chat_completions")
    return (os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_BASE_URL"), "responses")


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_default_model: str
    llm_provider: str
    llm_api_key: str | None
    llm_base_url: str | None
    llm_api_type: str
    llm_disable_tracing: bool
    llm_site_url: str | None
    llm_app_name: str | None
    rainfall_model: str
    tide_model: str
    warning_model: str
    forecast_model: str
    lightning_model: str
    compound_model: str
    synthesis_model: str
    hko_timeout_seconds: float
    hko_retries: int
    agent_timeout_seconds: float
    agent_retry_timeout_seconds: float
    peer_query_timeout_seconds: float
    log_dir: Path


def get_settings() -> Settings:
    llm_provider = os.getenv("FLOOD_SWARM_LLM_PROVIDER", "openai").strip().lower()
    provider_key, provider_base_url, provider_api_type = _provider_defaults(llm_provider)
    default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-5.4-mini")
    log_dir = Path(os.getenv("FLOOD_SWARM_LOG_DIR", "logs")).resolve()
    llm_api_key = os.getenv("FLOOD_SWARM_LLM_API_KEY", provider_key)
    llm_base_url = os.getenv("FLOOD_SWARM_LLM_BASE_URL", provider_base_url)
    llm_api_type = os.getenv("FLOOD_SWARM_LLM_API_TYPE", provider_api_type).strip().lower()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_default_model=default_model,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        llm_api_type=llm_api_type,
        llm_disable_tracing=_env_flag(
            "FLOOD_SWARM_DISABLE_TRACING",
            default=llm_provider != "openai",
        ),
        llm_site_url=os.getenv("FLOOD_SWARM_LLM_SITE_URL"),
        llm_app_name=os.getenv("FLOOD_SWARM_LLM_APP_NAME", "hk-flood-swarm"),
        rainfall_model=os.getenv("FLOOD_SWARM_RAINFALL_MODEL", default_model),
        tide_model=os.getenv("FLOOD_SWARM_TIDE_MODEL", default_model),
        warning_model=os.getenv("FLOOD_SWARM_WARNING_MODEL", default_model),
        forecast_model=os.getenv("FLOOD_SWARM_FORECAST_MODEL", default_model),
        lightning_model=os.getenv("FLOOD_SWARM_LIGHTNING_MODEL", default_model),
        compound_model=os.getenv("FLOOD_SWARM_COMPOUND_MODEL", default_model),
        synthesis_model=os.getenv("FLOOD_SWARM_SYNTHESIS_MODEL", default_model),
        hko_timeout_seconds=float(os.getenv("HKO_TIMEOUT_SECONDS", "15")),
        hko_retries=int(os.getenv("HKO_RETRIES", "2")),
        agent_timeout_seconds=float(os.getenv("FLOOD_SWARM_AGENT_TIMEOUT_SECONDS", "30")),
        agent_retry_timeout_seconds=float(
            os.getenv("FLOOD_SWARM_AGENT_RETRY_TIMEOUT_SECONDS", "15")
        ),
        peer_query_timeout_seconds=float(
            os.getenv("FLOOD_SWARM_PEER_QUERY_TIMEOUT_SECONDS", "8")
        ),
        log_dir=log_dir,
    )
