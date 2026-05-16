import importlib
import sys
from pathlib import Path


def test_settings_module_loads_dotenv_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        '\n'.join(
            [
                'FLOOD_SWARM_LLM_PROVIDER="mistral"',
                'MISTRAL_API_KEY="dotenv-test-key"',
                'OPENAI_DEFAULT_MODEL="mistral-small-latest"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FLOOD_SWARM_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_DEFAULT_MODEL", raising=False)
    sys.modules.pop("app.settings", None)
    settings_module = importlib.import_module("app.settings")
    settings = settings_module.get_settings()
    assert settings.llm_provider == "mistral"
    assert settings.llm_api_key == "dotenv-test-key"
    assert settings.openai_default_model == "mistral-small-latest"
