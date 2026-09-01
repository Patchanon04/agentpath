"""A tiny MCP server, used the same way the mock LLM server is used.

Testing an MCP client against somebody else's server means installing it,
running it, and hoping it behaves the same tomorrow. This server is ours, it
starts in milliseconds, and it answers the same way every time, so the
lesson checks and continuous integration can prove the client works without
depending on anything outside this repository.

It speaks the part of the protocol the client actually uses, which is
initialize, tools/list and tools/call, as JSON-RPC messages one per line
over standard input and output.
"""
import json
import sys

TOOLS = [
    {
        "name": "echo",
        "description": "Return the text you were given, unchanged.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Anything at all"}},
            "required": ["text"],
        },
    },
    {
        "name": "add",
        "description": "Add two numbers and return the sum.",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "explode",
        "description": "Always fail, so a client can be tested against a failing tool.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
]


def text_result(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def call_tool(name, arguments):
    if name == "echo":
        return text_result(str(arguments.get("text", "")))
    if name == "add":
        try:
            return text_result(str(arguments["a"] + arguments["b"]))
        except (KeyError, TypeError) as error:
            return text_result(f"bad arguments, {error}", is_error=True)
    if name == "explode":
        return text_result("this tool always fails on purpose", is_error=True)
    return text_result(f"unknown tool {name}", is_error=True)


def handle(message):
    """Return a response for one request, or None for a notification."""
    method = message.get("method")
    identifier = message.get("id")

    if identifier is None:
        # A notification such as notifications/initialized. Nothing to answer.
        return None

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "agentpath-mock", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        result = call_tool(params.get("name", ""), params.get("arguments") or {})
    else:
        return {
            "jsonrpc": "2.0",
            "id": identifier,
            "error": {"code": -32601, "message": f"method not found {method}"},
        }
    return {"jsonrpc": "2.0", "id": identifier, "result": result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(message)
        if response is not None:
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
