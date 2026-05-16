import os

from app.settings import get_settings


def test_openrouter_settings_are_resolved(monkeypatch):
    monkeypatch.setenv("FLOOD_SWARM_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    settings = get_settings()
    assert settings.llm_provider == "openrouter"
    assert settings.llm_api_key == "or-key"
    assert settings.llm_base_url == "https://openrouter.ai/api/v1"
    assert settings.llm_api_type == "chat_completions"
    assert settings.llm_disable_tracing is True


def test_custom_provider_allows_explicit_base_url(monkeypatch):
    monkeypatch.setenv("FLOOD_SWARM_LLM_PROVIDER", "custom")
    monkeypatch.setenv("FLOOD_SWARM_LLM_API_KEY", "custom-key")
    monkeypatch.setenv("FLOOD_SWARM_LLM_BASE_URL", "https://example.test/v1")
    settings = get_settings()
    assert settings.llm_provider == "custom"
    assert settings.llm_api_key == "custom-key"
    assert settings.llm_base_url == "https://example.test/v1"
    assert settings.llm_api_type == "chat_completions"
