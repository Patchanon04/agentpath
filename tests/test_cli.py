import pytest

from agentpath.cli import build_provider, build_tools, main


def test_builds_openai_provider_by_default(monkeypatch):
    monkeypatch.setenv("AGENTPATH_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    monkeypatch.setenv("AGENTPATH_API_KEY", "")
    assert build_provider("openai").__class__.__name__ == "OpenAICompatProvider"


def test_builds_anthropic_provider_on_request(monkeypatch):
    monkeypatch.setenv("AGENTPATH_BASE_URL", "https://api.anthropic.com/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    monkeypatch.setenv("AGENTPATH_API_KEY", "x")
    assert build_provider("anthropic").__class__.__name__ == "AnthropicProvider"


def test_missing_configuration_gives_a_readable_message(monkeypatch, capsys):
    monkeypatch.delenv("AGENTPATH_BASE_URL", raising=False)
    monkeypatch.delenv("AGENTPATH_MODEL", raising=False)
    with pytest.raises(SystemExit) as exit_info:
        main(["chat"])
    assert exit_info.value.code == 2
    assert "AGENTPATH_BASE_URL" in capsys.readouterr().err


def test_the_default_tool_set(tmp_path):
    names = {schema["name"] for schema in build_tools(tmp_path).schemas()}
    assert names == {
        "read_file",
        "write_file",
        "edit_file",
        "list_files",
        "run_shell",
        "glob_files",
        "grep_files",
        "search_notes",
    }


def test_read_only_tools_are_marked_safe_and_the_rest_are_not(tmp_path):
    """A tool that changes something must never be approved without asking."""
    registry = build_tools(tmp_path)
    names = {schema["name"] for schema in registry.schemas()}
    safe = {name for name in names if registry.get(name).safe}
    assert safe == {"read_file", "list_files", "glob_files", "grep_files", "search_notes"}


def test_all_three_commands_exist():
    for command in ["chat", "run", "resume"]:
        with pytest.raises(SystemExit) as exit_info:
            main([command, "--help"])
        assert exit_info.value.code == 0


def test_run_requires_a_task():
    with pytest.raises(SystemExit) as exit_info:
        main(["run"])
    assert exit_info.value.code == 2


def test_resume_with_no_name_lists_sessions(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AGENTPATH_HOME", str(tmp_path))
    monkeypatch.setenv("AGENTPATH_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    from agentpath.session import Session
    from agentpath.types import Message

    Session("earlier").append(Message(role="user", content="hello"))
    assert main(["resume"]) == 0
    assert "earlier" in capsys.readouterr().out


def test_resuming_a_session_that_does_not_exist_reports_it(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AGENTPATH_HOME", str(tmp_path))
    monkeypatch.setenv("AGENTPATH_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    assert main(["resume", "--session", "nope"]) == 1
    assert "does not exist" in capsys.readouterr().err
