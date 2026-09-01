[อ่านภาษาไทย](README.th.md)

# Lesson 19. The MCP client

## Welcome to part 4

Part 1 built an agent. Part 2 gave it real tools. Part 3 made it survivable,
which is a different axis entirely, and lesson 18 spent a whole chapter proving
that the difference between capable and operable is real and measurable.

Part 4 is about the limits of one agent, alone, using only the tools you
personally wrote, with no instrument for telling whether any change you make is
an improvement. Three limits, and each one gets chapters.

This chapter connects the agent to tools somebody else wrote. Lesson 20 lets it
delegate work to another agent with its own fresh context, and lesson 21 runs
several of those at once. Lesson 22 finally gives you the instrument, a task
runner and a judge, so that "I think the new prompt is better" becomes an
experiment you run instead of a feeling you have. Lesson 23 packages the whole
thing.

Now the part you should expect rather than be surprised by. **The agent loop
does not change in this part either.**

Lesson 11 measured that. Lesson 18 measured it again with a table of file
hashes, and the finding was exact. Tools never touched the loop. Subsystems
always did. This chapter adds an entire protocol, a second process, a
handshake, and a class of tool that did not exist when the program started, and
`agent.py` is byte for byte what it was in lesson 17.

```bash
cd lessons
for f in agent.py permissions.py session.py context.py providers.py usage.py \
         retry.py cancel.py prompt.py retrieval.py; do
  diff -qs 18-the-harness/$f 19-mcp-client/$f
done
```

```text
Files 18-the-harness/agent.py and 19-mcp-client/agent.py are identical
Files 18-the-harness/permissions.py and 19-mcp-client/permissions.py are identical
Files 18-the-harness/session.py and 19-mcp-client/session.py are identical
Files 18-the-harness/context.py and 19-mcp-client/context.py are identical
Files 18-the-harness/providers.py and 19-mcp-client/providers.py are identical
Files 18-the-harness/usage.py and 19-mcp-client/usage.py are identical
Files 18-the-harness/retry.py and 19-mcp-client/retry.py are identical
Files 18-the-harness/cancel.py and 19-mcp-client/cancel.py are identical
Files 18-the-harness/prompt.py and 19-mcp-client/prompt.py are identical
Files 18-the-harness/retrieval.py and 19-mcp-client/retrieval.py are identical
```

By now that should read as the expected result rather than as a claim. If
connecting to an external tool server had required editing the loop, the seam
between the loop and the tool registry would have been cut in the wrong place,
and eighteen chapters of argument about where boundaries go would have been
wrong.

Here is what is in this folder.

```text
lessons/19-mcp-client/
  mcp.py               new. the whole client, around 190 lines with docstrings
  mock_mcp_server.py   new. a tiny MCP server so the check needs nothing external
  check.py             new. five claims about the client
  tools.py             lesson 18, plus one 8 line function called register_mcp
  main.py              identical to lesson 18
  agent.py             identical to lesson 17
  permissions.py       identical to lesson 12
  session.py           identical to lesson 13
  context.py           identical to lesson 14
  providers.py         identical to lesson 17
  usage.py             identical to lesson 15
  retrieval.py         identical to lesson 16
  prompt.py            identical to lesson 10
  retry.py             identical to lesson 17
  cancel.py            identical to lesson 17
  README.md            this file
```

Outside the three new files, `tools.py` is the only file that changed at all,
and the change is seventeen lines at the bottom of it. Every other file in the
folder, `main.py` included, is byte for byte what lesson 18 shipped.

```bash
diff 18-the-harness/tools.py 19-mcp-client/tools.py
```

```python
# Lesson 19 lets tools arrive from another process at run time.


def register_mcp(schemas, functions):
    """Add tools discovered from an MCP server to the ones we wrote ourselves.

    Nothing else changes. The agent loop, the permission check and the
    registry all treat these exactly like read_file.
    """
    SCHEMAS.extend(schemas)
    FUNCTIONS.update(functions)


# Tools we did not write are never on the safe list, so every one of them
# goes through the permission gate from lesson 12.
```

Two statements and two comments. That is the cost, in this codebase, of being
able to use every MCP server anybody ever writes.

## 1. The problem part 3 left behind

Section 7 of lesson 18 named this limit and then walked away from it. Here it
is again, stated as the thing this chapter has to solve.

Count the tools your agent has. `read_file`, `write_file`, `edit_file`,
`list_files`, `run_shell`, `glob_files`, `grep_files`, `search_notes`. Eight.
Every one of them lives in `tools.py`, and every one of them was written by
you, by hand, with a schema, a dispatch entry, error handling, a permission
decision and a `check.py`.

That is a genuinely useful set for editing code in a folder. It is also the
complete list of things this agent can do, forever, unless you write more.

Now try to want a ninth. Ask this agent to read a row out of your Postgres
database. Ask it to open a page in a browser and tell you what is on it. Ask it
to look up the ticket you are working on, or to check whether the deploy went
out, or to search your team's documentation, or to look at a design file. The
answer to every one of those is the same. Go and write a tool.

Then write another. Then another. Each one is a schema you have to get right, a
dispatch entry, a decision about what a failure returns, an argument about
whether it belongs in `SAFE_TOOLS`, and a check that proves it works. Doing that
eight times took most of part 2.

Here is the part that should annoy you. Somebody has already written a good
Postgres tool. Somebody has written a good browser tool, and a good ticket tool,
and they are better than the ones you would write in an afternoon because they
have been used by thousands of people and had the sharp edges filed off. And
there is no way at all for your agent to use any of them.

The reason is one line, and it is a line you wrote on purpose.

```python
def run(name, arguments):
    function = FUNCTIONS.get(name)
```

`FUNCTIONS` is a dictionary of Python functions living in this process. A tool,
as far as this program is concerned, is a Python callable that has been imported
into this interpreter. Anything that is not that does not exist.

The seam that made part 2 work, where a tool is just a name in a dictionary and
the loop knows nothing else about it, is exactly the seam that closes here.
It is a good seam. It is just drawn around the wrong process.

## 2. What MCP actually is

Strip away the branding and the specification document and the ecosystem, and
the Model Context Protocol is one sentence.

**A server is a separate program that announces what it can do and does it when
asked.**

That is it. There are three messages you care about. You ask a server to
`initialize`, which is the handshake where both sides say who they are. You ask
`tools/list`, and it hands you back a list of tools with names, descriptions and
JSON Schemas for their arguments. You send `tools/call` with a name and some
arguments, and it does the thing and hands back the result.

Notice what that list of tools looks like when it arrives.

```json
{
  "name": "add",
  "description": "Add two numbers and return the sum.",
  "inputSchema": {
    "type": "object",
    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
    "required": ["a", "b"]
  }
}
```

Now look at what the model wants, which you have been building by hand since
lesson 03.

```json
{
  "type": "function",
  "function": {
    "name": "add",
    "description": "Add two numbers and return the sum.",
    "parameters": {"type": "object", "properties": {"...": "..."}}
  }
}
```

They are the same three fields wearing different clothes. Name, description,
JSON Schema. That is not a coincidence and it is the reason this whole chapter
is short. The conversion from what a server announces into what a model reads is
a rename of two keys, which is why `mcp_schemas` is thirty lines and most of
those are the docstring.

### Why this matters, and it is not because it is a standard

The usual pitch for MCP is that it is an open standard with wide adoption, which
is true and which is not a reason for you to care about anything. Standards are
worth adopting when the thing they standardise was painful, and worth ignoring
when it was not.

The reason to care is the one from section 1. Every capability in the world that
somebody has bothered to package as an MCP server is now a capability your agent
has, and the amount of code you write to get it is zero. Not "a small adapter".
Zero. You run a command and read a list.

Sit with what that changes about your job. Before this chapter, the question
"can the agent do X" was answered by "how long would it take me to write X".
After this chapter it is answered by "has anybody written X", and the second
question has a much better hit rate than the first.

That is the whole argument. It is a distribution mechanism for capability, and
it happens to be specified as a protocol because that is the only way a
distribution mechanism can work across languages and companies. If the same
thing arrived tomorrow under a different name with a different wire format, the
reason to use it would be identical.

### The two honest limits of what we build here

Stated at the top of `mcp.py` rather than discovered by you at midnight.

This client speaks the **stdio transport only**. The server is a subprocess and
we talk to it through its standard input and output. MCP also defines an HTTP
transport, and a server that only speaks HTTP will not work with this file at
all. That is a real restriction, and it is the right one for a lesson, because
the stdio case is where the protocol is visible and the HTTP case adds a
transport you already understand from lesson 01 without adding any protocol.

And **every tool it discovers is marked as not safe**. Section 7 is entirely
about why.

## 3. Why we are writing the client and not installing one

There is an official MCP SDK. `pip install mcp` and you are done in four lines.
We are not using it, for the same reason lesson 01 wrote an HTTP request by hand
instead of importing a provider library.

The argument then was that a library that hides the request also hides the fact
that the entire conversation is resent on every call, and that fact turns out to
explain most of the cost and most of the limits in the rest of the course. You
cannot reason about a thing you have never seen.

The same applies here, with a sharper edge. The part of MCP an agent actually
needs is three methods. Look at the size of it.

```bash
grep -c "" mcp.py
```

```text
188
```

One hundred and eighty eight lines including a seventeen line module docstring and
comments that explain the reasoning. The real code is a class with six methods
and one function. You can read the whole protocol in ten minutes, and afterwards
you will know exactly what happens when a server hangs, exactly what `isError`
means, exactly why the tool names have a prefix, and exactly what those tools
are costing you on every request.

Install the SDK first and all four of those are behind an abstraction. When your
agent then silently stops answering because a server never got its
`initialized` notification, you have no model of the system at all, and you are
reading someone else's async internals under time pressure, which is the worst
possible moment to learn a protocol.

Now be fair about the other side, because the argument does not extend as far as
people like to push it.

**Use the SDK in your own project.** Once you have read this file, you know what
the library is doing, and at that point the library is strictly better than this
one. It handles the HTTP and SSE transports. It handles servers that send
notifications about their tool list changing. It handles resources and prompts
and sampling, which are parts of the protocol this client ignores completely
because an agent does not need them to call a tool. It has been tested against
hundreds of real servers with their individual quirks, and this file has been
tested against one server that we wrote to be well behaved.

The rule is the same one from lesson 01. Write it once to understand it, then
use the library, and be the person on the team who can debug it when it breaks.

## 4. JSON-RPC over a pipe, one line at a time

Time to look at the actual bytes. The transport is the least mysterious thing in
this chapter and seeing it removes most of the mystery from the rest.

A server is a program. You start it as a subprocess. You write JSON to its
standard input, one object per line, and you read JSON from its standard output,
one object per line. That is the whole transport.

```python
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
```

Four of those arguments are load bearing and worth naming.

`stderr=subprocess.DEVNULL` because stdout is the protocol channel and nothing
else may be on it. Servers print debug noise to stderr constantly. Merge the two
and the first log line the server writes becomes a line your JSON parser chokes
on.

`text=True` with `encoding="utf-8"` because otherwise you are reading bytes and
decoding by hand, and because the default encoding on Windows is not UTF-8, so a
server that returns any non ASCII character produces mojibake or an exception on
one platform and works fine on another.

`bufsize=1` is line buffering. Without it Python may sit on your request in a
buffer while you wait for a reply that cannot arrive because you have not
actually sent anything. We also call `flush()` explicitly after every write,
which is the belt to that pair of braces.

### A real exchange, by hand

You do not need the client to see this. The server is a program that reads lines,
so pipe lines into it.

```bash
cd lessons/19-mcp-client
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"agentpath","version":"1.0.0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python mock_mcp_server.py
```

```text
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "agentpath-mock", "version": "1.0.0"}}}
{"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "echo", "description": "Return the text you were given, unchanged.", "inputSchema": {"type": "object", "properties": {"text": {"type": "string", "description": "Anything at all"}}, "required": ["text"]}}, {"name": "add", "description": "Add two numbers and return the sum.", "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}, {"name": "explode", "description": "Always fail, so a client can be tested against a failing tool.", "inputSchema": {"type": "object", "properties": {}, "required": []}}]}}
```

Three lines went in and two came back. Read the shape of it.

### id, method, params, result

JSON-RPC has exactly four fields you care about and they are all visible above.

**`method`** is the name of the thing you are asking for. `initialize`,
`tools/list`, `tools/call`. The slash is just part of a name, not a path.

**`params`** is the arguments to that method, always an object. For `initialize`
it carries the protocol version you speak, the capabilities you have, and who
you are. For `tools/list` it is empty. For `tools/call` it is the tool name and
the tool's own arguments, nested one level down.

**`id`** is how you match an answer to a question. You pick it, the server
echoes it back unchanged. Ours is a counter.

```python
            self._next_id += 1
            identifier = self._next_id
```

**`result`** is the answer, present when the call worked. When it did not work
there is an `error` object instead, with a `code` and a `message`, and never
both `result` and `error` in the same message.

```python
                if "error" in message:
                    raise MCPError(message["error"].get("message", "unknown server error"))
                return message.get("result") or {}
```

That distinction matters more than it looks and section 6 is about it. An
`error` at this level means the **server** failed, as in the method does not
exist or the request was malformed. A tool that ran and did not like its
arguments is a completely different thing and arrives inside `result`.

There is also a `jsonrpc` field which is always the string `"2.0"` and which you
will never think about again.

### The two shapes of message

Look at the second line we piped in.

```json
{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
```

No `id`. That is the entire difference between a request and a notification. A
message with an id expects an answer. A message without one does not, and must
not get one. That is why three lines in produced two lines out.

The server handles it in three lines and a comment.

```python
    if identifier is None:
        # A notification such as notifications/initialized. Nothing to answer.
        return None
```

And the client has a separate method for sending them, precisely so that no
caller can accidentally sit waiting for a reply to a message that will never get
one.

```python
    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})
```

### Now the same thing through the client

```bash
python -c "
import sys
from mcp import MCPClient
with MCPClient([sys.executable, 'mock_mcp_server.py']) as client:
    print('server name:', client.server_name)
    for t in client.list_tools():
        print(' -', t['name'], '|', t['description'])
    print('echo  ->', repr(client.call_tool('echo', {'text': 'across a pipe'})))
    print('add   ->', repr(client.call_tool('add', {'a': 2, 'b': 3})))
"
```

```text
server name: agentpath-mock
 - echo | Return the text you were given, unchanged.
 - add | Add two numbers and return the sum.
 - explode | Always fail, so a client can be tested against a failing tool.
echo  -> 'across a pipe'
add   -> '5'
```

`with` starts the process and does the handshake, and closes the pipe and reaps
the process on the way out. `connect` and `close` are also public, because
`check.py` and any long lived agent want to hold a server open across many
turns rather than for one block.

Note what `list_tools` is doing to the shape of the program. It is a **run time**
discovery. Nothing in this repository knows that a tool called `add` exists until
that call returns. Every tool before this chapter was a name typed into
`tools.py` by a person. These are not, and that is the actual novelty here, more
than the protocol is.

## 5. Two things that will bite you

Both of these are in the code with comments on them, and both produce symptoms
that point at the wrong place.

### One. The initialized notification is not optional

The handshake is two steps, not one. You send `initialize` and read the answer.
Then you send a notification called `notifications/initialized` with no id and
no answer.

```python
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
```

That second message looks like ceremony. It is not. It is the client saying that
it has read the server's capabilities and is now ready, and **many servers
refuse to process anything until it arrives.**

Here is why this one is worth a section instead of a line. Skip it and the
failure is not an error. You send `tools/list`, the server declines to answer
because you never finished the handshake, and your client sits in
`stdout.readline()` waiting for a line that is never going to be written. There
is no exception, no message, no exit code. The program stops.

So the symptom is a hang, and a hang sends you looking for a deadlock, a
buffering problem, a subprocess that failed to start, or a network stall. You
will check `bufsize`. You will check whether the server crashed. You will add
prints. All of those are the wrong place, because nothing is broken. The server
is politely waiting for a message you decided not to send, and it will wait
forever because that is what the protocol says it should do.

Two mistakes that produce identical hangs and are worth knowing about while you
are in there. A server command that does not exist starts fine as far as
`Popen` is concerned and then dies, so read the guard in `_send`.

```python
        if self.process is None or self.process.poll() is not None:
            raise MCPError("the server is not running")
```

`poll()` returns the exit code if the process has finished, so a dead server
turns into an exception on the next write rather than into a silent wait on a
closed pipe. And a server that closes its output turns into an exception rather
than an empty string that gets parsed as JSON.

```python
                if not line:
                    raise MCPError(f"the server closed while waiting for {method}")
```

Be honest about one gap while we are here. `MCPClient.__init__` takes a
`timeout` argument and stores it, and nothing in the file ever reads it. A read
that blocks forever is still possible, from a server that is alive, has not
closed anything, and is simply never going to answer. Closing that gap means a
reader thread with a queue, or non blocking reads, and it is genuinely more
machinery than this chapter can carry. The argument is left in place because
that is where it belongs when you add it, and naming a gap is better than
letting the parameter imply it is handled.

### Two. Read until the id matches

The obvious implementation of a request is to write a line and read a line.

```python
# what you would write first, and it is wrong
self._send(request)
return json.loads(self.process.stdout.readline())["result"]
```

That works, right up until it does not, and the way it fails is horrible.

A server may send messages at any time that are not answers to your question.
Log messages, progress notifications, a notification saying its tool list
changed. None of them carry your id, because none of them are replies. So the
next line out of the pipe is frequently not the thing you asked for.

Take the first line and you get a `KeyError` on `result` if you are lucky,
because a notification has no `result` field. If you are unlucky you get an
empty dictionary and carry on with a tool result that is actually a log line,
and every subsequent answer in the session is off by one, because the reply you
skipped is still sitting in the pipe waiting to be mistaken for the next one.

So the loop reads until the id matches and discards everything else.

```python
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
```

Four `continue` statements, and each one is a specific thing servers really do.
Blank lines. Lines that are not JSON, which is what a server printing to the
wrong stream looks like. Notifications, which have no id at all, so
`message.get("id")` is `None` and never equals your integer. And replies to some
other request.

The last one is why the whole method sits inside a lock.

```python
        with self._lock:
```

Two threads sending requests down one pipe at the same time would interleave
their writes, and each would then be racing the other to read a reply that might
belong to either of them. The lock makes the whole send and read one atomic
operation. This costs concurrency, since a slow tool call blocks a second thread
that only wanted to list tools, and for a client this size that is the correct
trade. Lesson 21 is where you find out which parts of your program quietly
assumed a single thread, and this one did not, on purpose.

## 6. A failing tool is not an exception

Lesson 07 established a rule that has held ever since. When a tool fails, the
failure is not an exception, it is a string that goes back into the conversation
as a tool result, because the model is the thing that can do something about it.

```python
# lesson 07
except FileNotFoundError:
    return f"Error: {path} does not exist"
```

The agent reads that, notices the path was wrong, calls `list_files`, and tries
again. Raise instead and the run ends with a traceback over a typo.

MCP has the same idea, spelled `isError`. Every `tools/call` reply carries
content and a flag.

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"explode","arguments":{}}}' \
  | python mock_mcp_server.py
```

```text
{"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "5"}], "isError": false}}
{"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "this tool always fails on purpose"}], "isError": true}}
```

Read those two lines carefully, because the important thing is what they have in
common. **Both are `result`.** Neither is a JSON-RPC `error`. The tool blew up
and the protocol still says the call succeeded, because from the protocol's point
of view it did. You asked the server to run a tool, and it ran the tool, and the
tool's opinion is that this went badly.

That is the same distinction the course has been making since lesson 07,
promoted to the wire format. The client just follows it.

```python
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
```

Three paths and each returns a string.

A **broken server** is caught and turned into text, because even that is
recoverable by the model, which can try a different tool or tell you what
happened rather than dying.

A **failing tool** becomes `Error: ` plus whatever the tool said. The prefix
matters. It is the same shape every other tool in `tools.py` uses, so a model
that has learned to recognise a failure from `read_file` recognises this one
without being told anything new.

A **successful tool** returns its text. Note that `content` is a list of blocks
and each block has a type, because MCP tools can return images and embedded
resources as well as text. We keep the text blocks and drop the rest, which is
an honest simplification. A server that returns a screenshot returns nothing
useful through this client, and handling that properly means the model has to
accept images, which is a chapter this course does not have.

Watch all three paths, plus the case where the server itself decides the
arguments were wrong.

```bash
python -c "
import sys
from mcp import MCPClient
with MCPClient([sys.executable, 'mock_mcp_server.py']) as client:
    print('add   ->', repr(client.call_tool('add', {'a': 2, 'b': 3})))
    print('add   ->', repr(client.call_tool('add', {'a': 2})))
    print('boom  ->', repr(client.call_tool('explode', {})))
"
```

```text
add   -> '5'
add   -> "Error: bad arguments, 'b'"
boom  -> 'Error: this tool always fails on purpose'
```

The middle line is the one to appreciate. A required argument was missing, the
server noticed, and the model gets told which key it forgot. It will supply `b`
and try again. Nothing crashed, nothing was lost, and the run continues.

## 7. Discovered tools are never safe

This section is not optional and it is not a disclaimer. It is the reason
`register_mcp` is eight lines instead of two.

Stop and consider what you just did. You started a program somebody else wrote,
on your machine, with your user account, and asked it what it can do. It
answered with a list of names and descriptions, and those descriptions are now
going into the context of a model that is going to decide, on its own, which of
them to run and with what arguments.

Three things are true at once, and each one on its own would be enough.

**You did not write these tools.** Every tool in part 2 came with an argument
about what it should refuse. `read_file` refuses to leave the workspace, because
`resolve_inside` compares the resolved path against `WORKSPACE`. `run_shell` has
a timeout. `edit_file` refuses an ambiguous match rather than guessing which
occurrence you meant. You know those rules exist because you wrote them and
argued about them for four chapters. You know none of that about a discovered
tool. It might confine itself to a directory. It might not. There is no field in
the protocol that tells you, and no field could, because a field is a claim.

**The description is whatever the author decided to claim.** This is the sharp
one. A tool description is not documentation checked by anything. It is a string
in a JSON object, written by the server author, that goes straight into your
model's context and is the entire basis on which the model decides to call the
tool. A tool called `get_weather` whose description says it returns the forecast
can do anything at all when you call it, and lesson 12 already taught you what
happens when untrusted text lands in the same context as your instructions. This
is worse than the prompt injection in lesson 12, because there the attacker's
text arrived in a file the agent read. Here it arrives in the tool list, before
the task starts, in the place the model treats as its own capabilities.

**The server is a program running on your machine.** Not a sandboxed function.
A subprocess, started by `subprocess.Popen`, with your file permissions, your
network access, your environment variables and therefore your API keys. Adding
an MCP server to your config is running somebody's code. It deserves the same
suspicion as `curl | sh` and it usually gets much less, because it arrives
through a friendly setup wizard.

So the rule is absolute and there is no exception to argue about.

```python
# Tools we did not write are never on the safe list, so every one of them
# goes through the permission gate from lesson 12.
```

Look at how that is enforced, because it is enforced by omission rather than by
a check, and omission is the stronger mechanism here.

```python
SAFE_TOOLS = {"read_file", "list_files", "glob_files", "grep_files"}
```

Four names, hard coded, all of them ours. `register_mcp` adds to `SCHEMAS` and
`FUNCTIONS` and it does not touch `SAFE_TOOLS`, and there is no code path
anywhere that can add to it at run time. So `Permissions.check` reaches its
first line, does not find the name, and falls through to asking a person.

```python
    def check(self, name, arguments):
        if name in SAFE_TOOLS:
            return True
```

The comment above the set in `permissions.py` is the design principle stated
plainly.

```python
# A tool missing from this set is treated as dangerous, which is the safe
# direction to be wrong in.
```

An allowlist fails closed. A blocklist fails open. If the gate had been "refuse
tools on this list of dangerous names", then every MCP tool would sail through by
default, and being wrong once would mean being wrong in the direction where
somebody's data is gone.

Now the tempting alternative, because you will want it within a day of using
this. MCP tools can carry annotations, including one called `readOnlyHint`. It
would be easy to read that and put read only tools on the safe list, and it would
remove a lot of prompts.

Do not. `readOnlyHint` is a claim made by the same author who wrote the tool and
the description. A tool that intends to be harmful sets it to true. The word
hint is doing real work in that name, and it is a hint for user interfaces, not a
security boundary. The only tools on the safe list are ones whose source you can
read in this repository.

The practical consequence is that connecting a chatty server to an agent with
`ask_in_terminal` is going to ask you a lot of questions, and you will be
tempted to reach for `--yes`. That tension is real and it is not resolved in this
chapter. The honest answer is that `--yes` is for a machine running a task you
already understand, that an MCP server you have audited and trust is a different
risk from one you installed this morning, and that the `[a]lways` option
remembers the full signature including arguments, so approving one specific call
forever does not approve the tool in general.

## 8. What those schemas cost, in real characters

This is the other required section, and it is the cost nobody mentions when they
tell you to connect twelve servers.

Every tool schema is sent on **every single request**. Not once at startup. Not
cached on the server. Lesson 01's finding, that the whole conversation is resent
every time, applies to the tool list too, and the tool list is sent before the
model has read one word of your task.

Do not take the argument, take the number. The last line of `check.py` measures
it by serialising `tools.SCHEMAS` before and after connecting.

```python
def schema_size():
    import json

    return len(json.dumps(tools.SCHEMAS))
```

```text
OK the schemas grew from 3101 to 3826 characters, 725 more on every request from one small server
```

**3101 characters** is your eight hand written tools, everything part 2 and part
3 built. **725 characters** is what one deliberately tiny server added. Three
tools, one sentence of description each, and the biggest input schema has two
properties.

That is roughly **242 characters per tool**, from the smallest server it is
possible to write.

### Now do the arithmetic for a real setup

Real servers are much fatter than ours, and not because their authors are
careless. A useful tool description is a paragraph, because the model has to
choose between this tool and eleven similar ones, and the input schema has ten
or fifteen properties with a description on each because that is how the model
knows what to put in them. Between 600 and 1500 characters per tool is entirely
ordinary.

Say you connect ten servers, which is not an extreme number, and say each offers
eight tools, which is modest. That is 80 tools.

| At this size per tool | 80 tools cost | Estimated tokens |
| --- | --- | --- |
| 242 characters, our toy server | 19,360 characters | around 4,800 |
| 800 characters, a realistic server | 64,000 characters | around 16,000 |
| 1,500 characters, a large server | 120,000 characters | around 30,000 |

The token column uses `CHARACTERS_PER_TOKEN = 4` from `context.py`, the same
rough estimator lesson 14 uses to decide when to trim.

Put the middle row against the default budget in lesson 18's `main.py`, which is
100,000. Sixteen percent of the entire context window is gone before the system
prompt, before your task, before the agent has read a single file. And it is
gone again on the next request, and the one after that, because the schemas are
resent every time. A twenty turn run pays that toll twenty times.

Then remember what lesson 14 does when the budget is reached. It drops the
oldest blocks, which are your original instructions. The schemas are not in that
list and cannot be trimmed, so what actually happens is that a fat tool list
pushes your own task out of the window. You paid tokens to make the agent
forget why it was working.

### The cost that is not tokens

Here is the part that surprises people, and it survives even if context windows
get big enough that nobody counts characters any more.

**A model choosing between sixty similarly named tools picks wrong more often.**

Three servers all offer something called search, or `find_files`, or `query`, and
their descriptions all say some variation of finding things. The model now has
to pick, from descriptions alone, with no ability to try one and see. It picks a
plausible wrong one, gets a result that is not useful but is not an error either,
and reasons onward from it. That failure has no exception, no log line and no
obvious symptom. It just looks like the agent being a bit stupid today.

You can watch this get worse as you connect servers. Eight tools with clearly
distinct jobs is an easy choice. Twenty is fine. Past forty, with overlap, the
error rate climbs and the reason is not the model being weak, it is that the
question genuinely got harder. You would pick wrong too, given sixty one line
descriptions and no way to experiment.

So the discipline is unpopular and simple. Connect the servers you need for the
task in front of you, not every server you have ever configured. Ten connected
servers is not a more capable agent than three. It is often a worse one that
also costs more.

### What people converged on in 2026

The answer the ecosystem has been moving toward is to stop sending everything.

Instead of putting all eighty full schemas in every request, you give the model
a short index. One line per tool, a name and a few words, and one extra tool
that fetches the full schema for a named tool on demand. The model reads the
index, decides it needs the Postgres one, asks for that schema, and gets it. You
have turned a fixed 64,000 character tax on every request into a few thousand
characters plus one extra round trip on the requests that actually need a tool.

If that sounds familiar it should. It is exactly lesson 16's argument about
retrieval, applied to tool definitions instead of documents. Do not put
everything in the context. Put in an index, and fetch on demand.

It is not free. The extra round trip costs latency, and a model that misreads a
one line summary never asks for the schema that would have corrected it, so you
have traded a token problem for a slightly worse discovery problem. But at eighty
tools that trade is clearly worth making, and at eight it is clearly not, which
is why this client does the simple thing and this section tells you where the
line is.

## 9. Name collisions

One more thing, small and nasty.

Two servers can both offer a tool called `search`. Nothing in the protocol
prevents it, and nothing could, because the servers do not know about each other.

`FUNCTIONS` is a dictionary. `SCHEMAS` is a list. Watch what happens when you
register two servers without a prefix.

```bash
python -c "
import sys
from mcp import MCPClient, mcp_schemas
import tools
a = MCPClient([sys.executable, 'mock_mcp_server.py']).connect()
b = MCPClient([sys.executable, 'mock_mcp_server.py']).connect()
tools.register_mcp(*mcp_schemas(a))
tools.register_mcp(*mcp_schemas(b))
names = [s['function']['name'] for s in tools.SCHEMAS]
print('schema list length:', len(tools.SCHEMAS))
print('dispatch table length:', len(tools.FUNCTIONS))
print('echo appears', names.count('echo'), 'times in the schemas')
a.close(); b.close()
"
```

```text
schema list length: 14
dispatch table length: 11
echo appears 2 times in the schemas
```

Fourteen schemas and eleven functions. The model is shown `echo` twice and can
only ever reach one of them, the second, because `FUNCTIONS.update` overwrote the
first. No error was raised. Nothing was logged. The first server's tools are
still connected, still running, and completely unreachable.

Now imagine those two servers were a staging database and a production database
that both expose `run_query`. The model calls `run_query`, gets an answer, and
neither you nor it has any way to know which database answered.

The fix is a prefix and it is the reason `mcp_schemas` takes one.

```python
    for described in client.list_tools():
        name = described["name"]
        exposed = f"{prefix}.{name}" if prefix else name
```

Pass one, from `check.py`, and the registry looks like this instead.

```bash
python -c "
import sys
from mcp import MCPClient, mcp_schemas
import tools
with MCPClient([sys.executable, 'mock_mcp_server.py']) as client:
    schemas, functions = mcp_schemas(client, prefix=client.server_name)
    tools.register_mcp(schemas, functions)
    print([s['function']['name'] for s in tools.SCHEMAS])
    print('via tools.run ->', repr(tools.run('agentpath-mock.add', {'a': 40, 'b': 2})))
"
```

```text
['read_file', 'write_file', 'edit_file', 'list_files', 'run_shell', 'glob_files',
 'grep_files', 'search_notes', 'agentpath-mock.echo', 'agentpath-mock.add',
 'agentpath-mock.explode']
via tools.run -> '42'
```

Now `agentpath-mock.echo` cannot collide with anything of ours and cannot collide
with another server. The prefix also does something useful for the model, which
is that it makes the ambiguous choice from section 8 slightly less ambiguous.
`staging.run_query` and `production.run_query` are two tools a model can
distinguish. Two tools called `run_query` are not.

The prefix is optional in the signature, because a single server with no
possibility of collision reads better without one, and because forcing it would
make the parameter feel like ceremony instead of a decision. Use it whenever
there could be more than one server, which in practice is always.

One detail in that function is worth pointing out because it is the kind of bug
that takes an hour to find.

```python
        def make(bound_name):
            def call(**arguments):
                return client.call_tool(bound_name, arguments)

            return call

        functions[exposed] = make(name)
```

The inner function is built by an outer function that takes the name as an
argument. The obvious version, defining `call` directly in the loop and closing
over `name`, does not work. Python closures capture the variable, not its value,
so by the time anything calls those functions the loop has finished and every
single one of them sees the last name in the list. All three of your tools would
call `explode`. Passing the name into `make` binds it to a fresh parameter per
iteration, which is what makes each closure remember its own tool.

## 10. Running check.py

```bash
cd lessons/19-mcp-client
python check.py
```

```text
OK connected and the server says it is agentpath-mock
OK 3 tools were discovered at run time, not written by us
OK agentpath-mock.echo ran in another process and the answer came back
OK a tool that fails on the server becomes text the model can read
OK the schemas grew from 3101 to 3826 characters, 725 more on every request from one small server
```

Five lines, one per section of this chapter. Take them in order.

**One. The handshake completed.** `client.server_name` is `agentpath-mock`,
which is a value that could only have come out of the `serverInfo` block in the
`initialize` reply. It proves the request went down the pipe, the reply came
back, and the id matched. If the `initialized` notification were missing this
line would still pass against our well behaved mock and would hang against a
real server, which is exactly why section 5 exists as prose rather than as a
check.

**Two. Tools were discovered at run time.** Three names that appear nowhere in
this repository outside `mock_mcp_server.py`, arriving as data rather than as
code. That is the sentence the whole lesson is about.

**Three. A discovered tool ran and the answer came back.** Look closely at how
that claim is made.

```python
        schemas, functions = mcp_schemas(client, prefix=client.server_name)
        tools.register_mcp(schemas, functions)

        name = f"{client.server_name}.echo"
        answer = tools.run(name, {"text": "across a pipe"})
```

It calls **`tools.run`**, not `client.call_tool`. That is deliberate and it is
the strongest claim in the file. It proves the registration worked, that the
prefixed name is in `FUNCTIONS`, that the closure bound the right tool name, and
that the ordinary dispatch path used by the agent loop reaches a function in
another process without knowing that it did. Calling the client directly would
have proved the client works and nothing about the integration.

**Four. A failing tool became readable text.** `explode` runs, the server sets
`isError`, and what comes back starts with `Error`. Not an exception, not a
traceback, a string a model can read and respond to, exactly like lesson 07.

**Five. The cost is a number you can see.** Section 8 in one line, and it fails
if connecting a server does not change the schema size at all, which would mean
`register_mcp` silently did nothing.

Or run every lesson at once, the way CI does.

```bash
python ci/run_lessons.py
```

If the first line fails and the run hangs instead of erroring, the handshake did
not complete, and the place to look is the `initialized` notification. If it
fails with the server closing, the command is wrong or the server crashed on
startup, and the quickest way to see the reason is to change
`stderr=subprocess.DEVNULL` to `stderr=None` temporarily so the server's own
error output reaches your terminal. If the third fails with an unknown tool, the
prefix in `mcp_schemas` and the prefix in the name you are calling have gone out
of sync.

## 11. What you cannot do yet

The agent can now use tools you did not write, and there is no limit on how many.
That is a real jump in capability and it took seventeen lines in `tools.py`.

It changed nothing at all about how the agent works.

Everything still happens in one conversation. One message list, one context
window, one model, one train of thought. Your task, the system prompt, every file
it read, every tool result, every dead end, all in the same list, growing.

Lesson 14 made that survivable rather than solved, and this chapter has quietly
made it worse in two ways. The schemas from section 8 are a fixed tax on every
request that trimming cannot touch. And the tools from section 7 are new sources
of large tool results, because a database query or a web page fetch returns far
more text than `read_file` does on a source file.

Watch what happens on a genuinely large job. The conversation fills. `fit_to_budget`
drops the oldest blocks, which contain your original instructions and the reason
the agent chose the approach it is three quarters of the way through. There is no
error, because trimming worked exactly as designed. The agent just gets slowly
stupider as the run goes on, forgetting the most load bearing parts of its own
reasoning, and the only symptom is that the work gets worse.

A bigger window does not fix this and neither does better trimming, because both
are answers to the wrong question. The problem is that one conversation is being
asked to hold a job that does not fit in one conversation.

**That is lesson 20.** Subagents. An agent that can start another agent with its
own fresh context, hand it one narrow piece of work, and get back a short answer
instead of a forty message transcript. The parent's conversation grows by one
paragraph rather than by everything the child had to read to write it. That
chapter also comes with the failure mode you get for free, which is that parent
and child now see different versions of the world, and the isolation that made
the child sharp is exactly what makes that worse.

Before you go on, connect a real MCP server to this client. A filesystem server
or anything else that runs over stdio will do. Then do two things. Print the tool
list and read the descriptions as if you were the model that has to choose
between them and your own eight. And run `check.py`'s schema measurement against
it, so the number in section 8 stops being an argument in a chapter and becomes a
figure you have seen on your own machine.

On to lesson 20.
