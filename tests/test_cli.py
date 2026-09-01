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


def test_the_eval_command_exists():
    with pytest.raises(SystemExit) as exit_info:
        main(["eval", "--help"])
    assert exit_info.value.code == 0


def test_eval_reports_failure_with_a_non_zero_exit_code(monkeypatch, tmp_path, capsys):
    """The exit code is what lets continuous integration refuse a bad change."""
    monkeypatch.setenv("AGENTPATH_BASE_URL", "http://127.0.0.1:1/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    tasks_file = tmp_path / "tasks.py"
    tasks_file.write_text(
        "from agentpath.evals import Task\n"
        "TASKS = [Task('always fails', 'hello', lambda answer, workspace: (False, 'no'))]\n",
        encoding="utf-8",
    )
    assert main(["eval", str(tasks_file), "--workspace", str(tmp_path)]) == 1
    assert "0 of 1 tasks passed" in capsys.readouterr().out


def test_eval_refuses_a_file_with_no_tasks(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AGENTPATH_BASE_URL", "http://127.0.0.1:1/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    empty = tmp_path / "empty.py"
    empty.write_text("NOTHING = 1\n", encoding="utf-8")
    assert main(["eval", str(empty)]) == 2
    assert "does not define TASKS" in capsys.readouterr().err


def test_mcp_tools_join_the_registry_through_the_command_line(monkeypatch, tmp_path):
    import sys as _sys

    from agentpath.cli import build_tools, connect_mcp

    registry = build_tools(tmp_path)
    before = set(schema["name"] for schema in registry.schemas())
    client = connect_mcp(
        registry, f'"{_sys.executable}" -m agentpath.testing.mock_mcp_server', 0
    )
    try:
        after = set(schema["name"] for schema in registry.schemas())
        assert "agentpath-mock.echo" in after - before
        assert registry.get("agentpath-mock.echo").safe is False
    finally:
        client.close()


def test_the_shell_tool_is_not_gated_twice(tmp_path):
    """Permissions decide. A tool that also asks would refuse a --yes run.

    The failure this prevents is not theoretical. With its own question in
    place, agentpath run --yes refused every command it had already been
    told to approve.
    """
    import sys

    from agentpath.types import ToolCall

    registry = build_tools(tmp_path)
    call = ToolCall("1", "run_shell", {"command": f'"{sys.executable}" -c "print(42)"'})
    assert registry.run(call).content.strip() == "42"


def test_clearing_a_cancellation_keeps_the_tools_working(tmp_path):
    """The tools hold the token, so it has to be cleared rather than replaced."""
    import sys

    from agentpath.cancel import Cancellation
    from agentpath.types import ToolCall

    cancellation = Cancellation()
    registry = build_tools(tmp_path, cancellation=cancellation)
    call = ToolCall("1", "run_shell", {"command": f'"{sys.executable}" -c "print(42)"'})

    assert registry.run(call).content.strip() == "42"
    cancellation.cancel()
    assert "Cancelled" in registry.run(call).content
    cancellation.reset()
    assert registry.run(call).content.strip() == "42"


def test_resuming_does_not_add_a_second_system_prompt(monkeypatch, tmp_path):
    """A duplicate system message can never be trimmed, so it must never be added."""
    import types as _types

    monkeypatch.setenv("AGENTPATH_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("AGENTPATH_BASE_URL", "http://127.0.0.1:1/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    from agentpath.cli import build_agent
    from agentpath.session import Session
    from agentpath.types import Message

    arguments = _types.SimpleNamespace(
        workspace=str(tmp_path), provider="openai", session="s",
        budget=1000, yes=True, mcp=None, verbose=False,
    )
    session = Session("s")
    build_agent(arguments, session)
    session.append(Message(role="user", content="hello"))

    for _ in range(3):
        agent, _ = build_agent(arguments, session, system=False)
        agent.messages = session.load()

    assert sum(1 for m in session.load() if m.role == "system") == 1
