"""Check that lesson 19 works.

Five things must be true. The handshake completes and the server tells us
who it is. Tools are discovered while the program is running rather than
being written into it. A discovered tool can be called and the answer comes
back. A tool that fails on the server becomes text the model can read. And
the cost of carrying those extra schemas is a number you can see, because
that cost is paid on every single request.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson19-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import tools  # noqa: E402
from mcp import MCPClient, mcp_schemas  # noqa: E402

SERVER = [sys.executable, str(Path(__file__).parent / "mock_mcp_server.py")]


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def schema_size():
    import json

    return len(json.dumps(tools.SCHEMAS))


def main():
    before = schema_size()

    with MCPClient(SERVER) as client:
        if client.server_name != "agentpath-mock":
            fail(f"the handshake did not report the server name. Got {client.server_name!r}")
        print(f"OK connected and the server says it is {client.server_name}")

        discovered = {tool["name"] for tool in client.list_tools()}
        if not {"echo", "add"} <= discovered:
            fail(f"tools were not discovered. Got {discovered}")
        print(f"OK {len(discovered)} tools were discovered at run time, not written by us")

        schemas, functions = mcp_schemas(client, prefix=client.server_name)
        tools.register_mcp(schemas, functions)

        name = f"{client.server_name}.echo"
        answer = tools.run(name, {"text": "across a pipe"})
        if answer != "across a pipe":
            fail(f"calling a discovered tool failed. Got {answer!r}")
        print(f"OK {name} ran in another process and the answer came back")

        broken = tools.run(f"{client.server_name}.explode", {})
        if not broken.startswith("Error"):
            fail(f"a failing tool did not come back as readable text. Got {broken!r}")
        print("OK a tool that fails on the server becomes text the model can read")

    after = schema_size()
    added = after - before
    if added <= 0:
        fail("connecting a server did not change the schema cost, which cannot be right")
    print(
        f"OK the schemas grew from {before} to {after} characters, "
        f"{added} more on every request from one small server"
    )


if __name__ == "__main__":
    main()
