"""A client for the Model Context Protocol, written by hand and kept small.

MCP is how an agent uses tools somebody else wrote. A server runs as a
separate process, announces what it can do, and does it when asked. That is
the whole idea, and it matters because it turns every MCP server in the
world into tools your agent can use without you writing any of them.

There is an official library. We are not using it, for the same reason we
did not use a model provider library in lesson 01. The part of the protocol
an agent actually needs is initialize, tools/list and tools/call, which is
JSON-RPC over a pipe and fits in this file. Reading it is the lesson.

Two limits are stated rather than hidden. This client speaks the stdio
transport only, so a server reachable over HTTP will not work. And every
tool it discovers is marked as not safe, because we did not write those
tools and cannot know what they do.
"""
import json
import subprocess
import threading

PROTOCOL_VERSION = "2024-11-05"


class MCPError(Exception):
    """Raised when the server itself fails, as opposed to a tool failing."""


class MCPClient:
    def __init__(self, command, timeout=30):
        self.command = list(command)
        self.timeout = timeout
        self.process = None
        self.server_name = ""
        self._next_id = 0
        self._lock = threading.Lock()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exception):
        self.close()

    def connect(self):
        """Start the server and complete the handshake.

        The handshake has two steps that both matter. We ask to initialize
        and read the answer, then we send an initialized notification with
        no id. Many servers refuse to do anything until that second message
        arrives, and forgetting it produces a server that simply never
        answers, which looks like a hang rather than a mistake.
        """
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        answer = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "agentpath", "version": "1.0.0"},
            },
        )
        self.server_name = (answer.get("serverInfo") or {}).get("name", "unknown")
        self._notify("notifications/initialized")
        return self

    def _send(self, message):
        if self.process is None or self.process.poll() is not None:
            raise MCPError("the server is not running")
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _request(self, method, params=None):
        """Send one request and read until the answer to it arrives.

        Reading until the id matches is not defensive programming. A server
        is allowed to send notifications and log messages at any moment, so
        the next line back is often not the answer to the question just
        asked. Taking the first line and hoping works until it does not.
        """
        with self._lock:
            self._next_id += 1
            identifier = self._next_id
            self._send(
                {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params or {}}
            )
            while True:
                line = self.process.stdout.readline()
                if not line:
                    raise MCPError(f"the server closed while waiting for {method}")
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("id") != identifier:
                    continue
                if "error" in message:
                    raise MCPError(message["error"].get("message", "unknown server error"))
                return message.get("result") or {}

    def list_tools(self):
        """Ask the server what it can do. This happens at run time, not build time."""
        return self._request("tools/list").get("tools", [])

    def call_tool(self, name, arguments):
        """Run one tool and return its output as text.

        A tool that fails is not an exception here. The server reports it
        with isError and the failure is something the model should read and
        respond to, exactly like the tool errors from lesson 07. A broken
        server comes back as text too, so that one dead server does not end
        the whole turn.
        """
        try:
            result = self._request("tools/call", {"name": name, "arguments": arguments})
        except MCPError as error:
            return f"Error: the MCP server failed, {error}"
        parts = [
            block.get("text", "")
            for block in result.get("content", [])
            if block.get("type") == "text"
        ]
        text = "\n".join(part for part in parts if part)
        if result.get("isError"):
            return f"Error: {text or 'the tool failed with no message'}"
        return text

    def close(self):
        if self.process is None:
            return
        try:
            self.process.stdin.close()
            self.process.wait(timeout=5)
        except Exception:
            self.process.kill()
        finally:
            self.process = None


def mcp_schemas(client, prefix=None):
    """Turn everything a server offers into schemas the model can read.

    Once this returns, nothing downstream knows or cares that these tools
    live in another process. They go into the same SCHEMAS list, they are
    checked by the same permission system, and the agent loop is unchanged.
    That is the payoff of having drawn the line where we drew it.

    prefix exists because two servers can both offer a tool called search.
    Without it the second one silently replaces the first.
    """
    schemas = []
    functions = {}
    for described in client.list_tools():
        name = described["name"]
        exposed = f"{prefix}.{name}" if prefix else name

        def make(bound_name):
            def call(**arguments):
                return client.call_tool(bound_name, arguments)

            return call

        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": exposed,
                    "description": described.get("description", ""),
                    "parameters": described.get("inputSchema")
                    or {"type": "object", "properties": {}},
                },
            }
        )
        functions[exposed] = make(name)
    return schemas, functions
