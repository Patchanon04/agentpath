import pytest

from agentpath.tools.base import Tool, ToolRegistry
from agentpath.types import ToolCall

ADD = Tool(
    name="add",
    description="Add two numbers",
    parameters={
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    },
    fn=lambda a, b: a + b,
)


def test_schemas_expose_name_description_parameters():
    schemas = ToolRegistry([ADD]).schemas()
    assert schemas == [
        {"name": "add", "description": "Add two numbers", "parameters": ADD.parameters}
    ]


def test_run_returns_string_content():
    result = ToolRegistry([ADD]).run(ToolCall(id="1", name="add", arguments={"a": 2, "b": 3}))
    assert result.content == "5"
    assert result.tool_call_id == "1"


def test_unknown_tool_becomes_an_error_result_not_a_crash():
    result = ToolRegistry([ADD]).run(ToolCall(id="1", name="nope", arguments={}))
    assert "unknown tool" in result.content


def test_bad_arguments_become_an_error_result_not_a_crash():
    result = ToolRegistry([ADD]).run(ToolCall(id="1", name="add", arguments={"a": 2}))
    assert result.content.startswith("Error")


def test_empty_registry_reports_no_schemas():
    assert ToolRegistry().schemas() == []


def test_malformed_arguments_are_reported_to_the_model_not_silently_dropped():
    call = ToolCall(
        id="1",
        name="add",
        arguments={},
        arguments_error='arguments were not valid JSON. Raw text was \'{"a": 2, "b\'',
    )
    result = ToolRegistry([ADD]).run(call)
    assert "not valid JSON" in result.content
    assert "Send the tool call again" in result.content


@pytest.mark.parametrize("arguments", [{"a": 1, "b": 2}, {"b": 2, "a": 1}])
def test_argument_order_does_not_matter(arguments):
    assert ToolRegistry([ADD]).run(ToolCall(id="1", name="add", arguments=arguments)).content == "3"


def test_schema_size_is_zero_for_an_empty_registry():
    assert ToolRegistry().schema_size() == 0


def test_schema_size_grows_with_every_tool_added():
    """The fixed cost of having tools, paid on every single request."""
    one = ToolRegistry([ADD]).schema_size()
    two = ToolRegistry([ADD, Tool("sub", "Subtract two numbers", ADD.parameters, lambda: 0)])
    assert two.schema_size() > one > 0
