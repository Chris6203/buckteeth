import os
from buckteeth.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    settings = Settings()
    assert settings.database_url == "postgresql+asyncpg://localhost/test"
    assert settings.anthropic_api_key == "sk-ant-test"
    assert settings.log_level == "INFO"
