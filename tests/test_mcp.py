import sys

import pytest

from agentpath.mcp import MCPClient, mcp_tools
from agentpath.tools.base import ToolRegistry
from agentpath.types import ToolCall

SERVER = [sys.executable, "-m", "agentpath.testing.mock_mcp_server"]


@pytest.fixture
def client():
    with MCPClient(SERVER) as connected:
        yield connected


def test_connecting_reports_the_server_name(client):
    assert client.server_name == "agentpath-mock"


def test_tools_are_discovered_at_run_time(client):
    names = {tool["name"] for tool in client.list_tools()}
    assert {"echo", "add", "explode"} <= names


def test_a_tool_can_be_called(client):
    assert client.call_tool("echo", {"text": "hello"}) == "hello"


def test_arguments_travel_correctly(client):
    assert client.call_tool("add", {"a": 2, "b": 3}) == "5"


def test_a_failing_tool_becomes_readable_text_rather_than_a_crash(client):
    result = client.call_tool("explode", {})
    assert result.startswith("Error")
    assert "on purpose" in result


def test_an_unknown_tool_is_reported_not_raised(client):
    assert "unknown tool" in client.call_tool("nope", {})


def test_one_process_serves_the_whole_session(client):
    """Reconnecting per call would restart the server every time."""
    first = client.process.pid
    client.call_tool("echo", {"text": "one"})
    client.call_tool("echo", {"text": "two"})
    assert client.process.pid == first


def test_mcp_tools_become_ordinary_tools():
    with MCPClient(SERVER) as client:
        registry = ToolRegistry(mcp_tools(client))
        result = registry.run(ToolCall("1", "echo", {"text": "through the registry"}))
        assert result.content == "through the registry"


def test_discovered_tools_are_never_marked_safe():
    """We did not write them, so they must go through the permission gate."""
    with MCPClient(SERVER) as client:
        assert all(not tool.safe for tool in mcp_tools(client))


def test_names_can_be_prefixed_to_avoid_collisions():
    with MCPClient(SERVER) as client:
        names = {tool.name for tool in mcp_tools(client, prefix="demo")}
        assert "demo.echo" in names
        registry = ToolRegistry(mcp_tools(client, prefix="demo"))
        assert registry.run(ToolCall("1", "demo.echo", {"text": "ok"})).content == "ok"


def test_closing_stops_the_process():
    client = MCPClient(SERVER)
    client.connect()
    process = client.process
    client.close()
    assert process.poll() is not None
