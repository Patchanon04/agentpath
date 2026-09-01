import pytest

from agentpath.cli import build_provider, main


def test_builds_openai_provider_by_default(monkeypatch):
    monkeypatch.setenv("AGENTPATH_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    monkeypatch.setenv("AGENTPATH_API_KEY", "")
    provider = build_provider("openai")
    assert provider.__class__.__name__ == "OpenAICompatProvider"


def test_builds_anthropic_provider_on_request(monkeypatch):
    monkeypatch.setenv("AGENTPATH_BASE_URL", "https://api.anthropic.com/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    monkeypatch.setenv("AGENTPATH_API_KEY", "x")
    provider = build_provider("anthropic")
    assert provider.__class__.__name__ == "AnthropicProvider"


def test_missing_configuration_gives_a_readable_message(monkeypatch, capsys):
    monkeypatch.delenv("AGENTPATH_BASE_URL", raising=False)
    monkeypatch.delenv("AGENTPATH_MODEL", raising=False)
    with pytest.raises(SystemExit) as exit_info:
        main(["chat"])
    assert exit_info.value.code == 2
    assert "AGENTPATH_BASE_URL" in capsys.readouterr().err
