from agentpath.agent import Agent
from agentpath.permissions import Permissions
from agentpath.providers.openai_compat import OpenAICompatProvider
from agentpath.subagent import subagent_tool
from agentpath.tools.base import Tool, ToolRegistry
from agentpath.tools.files import file_tools
from agentpath.types import ToolCall, ToolResult

WRITE_TASK = 'Write it. [[tool:write_file:{"path": "made-by-child.txt", "content": "hello"}]]'


def build_provider(mock_url):
    return OpenAICompatProvider(base_url=f"{mock_url}/v1", api_key="unused", model="mock")


def test_a_subagent_is_an_ordinary_tool():
    tool = subagent_tool(lambda: None)
    assert isinstance(tool, Tool)
    assert "task" in tool.parameters["properties"]


def test_a_subagent_is_never_safe_by_default():
    """It can do anything its own tools can do, so it goes through the gate."""
    assert subagent_tool(lambda: None).safe is False


def test_the_child_does_real_work_that_reaches_disk(mock_url, tmp_path):
    def build_child():
        return Agent(
            provider=build_provider(mock_url),
            tools=ToolRegistry(file_tools(tmp_path)),
            permissions=Permissions(auto_approve=True),
        )

    registry = ToolRegistry([subagent_tool(build_child)])
    result = registry.run(ToolCall("1", "run_subagent", {"task": WRITE_TASK}))
    assert isinstance(result, ToolResult)
    assert (tmp_path / "made-by-child.txt").read_text(encoding="utf-8") == "hello"


def test_the_child_history_does_not_land_in_the_parent(mock_url, tmp_path):
    """Context isolation is the whole reason to use a subagent.

    The child does several turns of work. The parent ends up with one tool
    result. That difference is the saving, and it is why a long
    investigation can be delegated without filling the parent up.
    """
    children = []

    def build_child():
        child = Agent(
            provider=build_provider(mock_url),
            tools=ToolRegistry(file_tools(tmp_path)),
            permissions=Permissions(auto_approve=True),
        )
        children.append(child)
        return child

    registry = ToolRegistry([subagent_tool(build_child)])
    registry.run(ToolCall("1", "run_subagent", {"task": WRITE_TASK}))

    assert children, "the subagent never ran"
    child = children[0]
    assert [m.role for m in child.messages] == ["user", "assistant", "tool", "assistant"]

    parent = Agent(
        provider=build_provider(mock_url),
        tools=registry,
        permissions=Permissions(auto_approve=True),
    )
    assert parent.messages == []


def test_every_call_gets_a_fresh_child(mock_url, tmp_path):
    built = []

    def build_child():
        child = Agent(
            provider=build_provider(mock_url),
            tools=ToolRegistry(file_tools(tmp_path)),
            permissions=Permissions(auto_approve=True),
        )
        built.append(child)
        return child

    registry = ToolRegistry([subagent_tool(build_child)])
    registry.run(ToolCall("1", "run_subagent", {"task": "Say hello."}))
    registry.run(ToolCall("2", "run_subagent", {"task": "Say hello."}))
    assert len(built) == 2
    assert built[0] is not built[1]


def test_a_child_that_explodes_does_not_kill_the_parent():
    def build_broken():
        raise RuntimeError("the child could not start")

    result = ToolRegistry([subagent_tool(build_broken)]).run(
        ToolCall("1", "run_subagent", {"task": "anything"})
    )
    assert result.content.startswith("Error")
    assert "could not start" in result.content


def test_the_parent_holds_a_stale_view_after_the_child_changes_a_file(mock_url, tmp_path):
    """The trap that comes with context isolation, demonstrated on purpose.

    The parent reads a file, the child rewrites it, and nothing tells the
    parent. This test does not prove the code is right. It proves the
    problem is real, which is what lesson 20 has to teach.
    """
    target = tmp_path / "shared.txt"
    target.write_text("original", encoding="utf-8")

    parent_tools = ToolRegistry(file_tools(tmp_path))
    parent_saw = parent_tools.run(ToolCall("1", "read_file", {"path": "shared.txt"})).content

    def build_child():
        return Agent(
            provider=build_provider(mock_url),
            tools=ToolRegistry(file_tools(tmp_path)),
            permissions=Permissions(auto_approve=True),
        )

    ToolRegistry([subagent_tool(build_child)]).run(
        ToolCall(
            "2",
            "run_subagent",
            {"task": 'Rewrite. [[tool:write_file:{"path": "shared.txt", "content": "changed"}]]'},
        )
    )

    assert parent_saw == "original"
    assert target.read_text(encoding="utf-8") == "changed"
