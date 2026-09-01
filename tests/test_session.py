import json

from agentpath.session import Session
from agentpath.types import Message, ToolCall


def test_a_message_survives_a_round_trip(tmp_path):
    session = Session("demo", directory=tmp_path)
    original = Message(
        role="assistant",
        content="working on it",
        tool_calls=[ToolCall(id="c1", name="add", arguments={"a": 1, "b": 2})],
    )
    session.append(original)
    assert Session("demo", directory=tmp_path).load() == [original]


def test_the_file_is_one_json_object_per_line(tmp_path):
    session = Session("demo", directory=tmp_path)
    session.append(Message(role="user", content="first"))
    session.append(Message(role="assistant", content="second"))
    lines = session.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["content"] for line in lines] == ["first", "second"]


def test_what_was_already_written_survives_a_crash(tmp_path):
    """Appending as we go is the whole reason for this format.

    We simulate a crash by simply never writing the last message, then
    loading the file. Everything that finished is still there.
    """
    session = Session("demo", directory=tmp_path)
    session.append(Message(role="user", content="asked"))
    session.append(Message(role="assistant", content="answered"))
    assert [m.content for m in Session("demo", directory=tmp_path).load()] == [
        "asked",
        "answered",
    ]


def test_loading_a_session_that_does_not_exist_is_empty_not_an_error(tmp_path):
    assert Session("never-used", directory=tmp_path).load() == []


def test_sessions_can_be_listed(tmp_path):
    Session("alpha", directory=tmp_path).append(Message(role="user", content="x"))
    Session("beta", directory=tmp_path).append(Message(role="user", content="y"))
    assert Session.list_all(tmp_path) == ["alpha", "beta"]


def test_thai_and_other_non_ascii_text_is_readable_in_the_file(tmp_path):
    """The file is for a person to read, so it must not be escaped away."""
    session = Session("demo", directory=tmp_path)
    session.append(Message(role="user", content="สวัสดี"))
    assert "สวัสดี" in session.path.read_text(encoding="utf-8")


def test_a_session_name_cannot_leave_the_folder(tmp_path):
    """The name arrives from a command line argument, so it is untrusted."""
    sneaky = Session("../../escaped", directory=tmp_path)
    assert sneaky.path.parent.resolve() == tmp_path.resolve()
    assert sneaky.name == "escaped"


def test_an_awkward_session_name_is_still_readable(tmp_path):
    """These files are read by eye, so the name must survive being made safe."""
    assert Session("fix login bug", directory=tmp_path).name == "fix-login-bug"
    assert Session("...", directory=tmp_path).name == "session"
