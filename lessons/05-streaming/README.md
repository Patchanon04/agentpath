[อ่านภาษาไทย](README.th.md)

# Lesson 05. Streaming

This is the hardest chapter in part one. Not the most important, that was
lesson 03, but the one with the most fiddly detail per paragraph. You are
about to take a piece of code that read one clean JSON document and turn it
into a piece of code that reads a stream of tiny fragments and reassembles
them. Half of that is easy. The other half, reassembling the arguments of a
tool call from pieces that are individually broken, is the part that makes
people close the tab.

So here is the reassurance up front. There is nothing clever in this lesson.
There is no new protocol to learn beyond about eight lines of text format,
no library to install, and no concurrency. The whole thing is a loop over
lines, an `if` statement, and a dictionary used as a buffer. If you read this
chapter slowly, the code in `llm.py` will look obvious by the end, and every
streaming client you ever read afterwards will look familiar. Take it in two
sittings if you need to. Section 3 and section 4 are genuinely separate
lessons that happen to live in one file.

Files in this folder.

```text
lessons/05-streaming/
  tools.py    unchanged from lesson 03, the same two toy tools
  llm.py      the API call, now reading a stream instead of one response
  agent.py    the lesson 04 loop, now printing text as it arrives
  check.py    a script that proves text and tool calls both survive streaming
  README.md   this file
```

## 1. The problem left over from lesson 04

Lesson 04 gave you a working agent. It asks the model, runs whatever tools
the model asks for, feeds the results back, and asks again until the model
answers in words. It is correct. It is also, as a thing to sit in front of,
faintly unpleasant.

Run it and watch what your terminal does.

```text
$ python agent.py
                                      <- nothing
                                      <- still nothing
                                      <- still nothing
[calling add with {'a': 2, 'b': 3}]
[add returned 5]
                                      <- nothing again
The answer is 5.
```

Against a fast hosted model that dead air is a second or two and you barely
notice. Against a model running on your own laptop it can be twenty or thirty
seconds, and thirty seconds of an unmoving cursor does not feel like waiting.
It feels like a crash. You start wondering whether you typed the URL wrongly,
whether the process is stuck, whether you should press control C. Several
times you will press control C on a program that was about to succeed.

The cause is visible in one line of lesson 04's `llm.py`.

```python
response = httpx.post(
    f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120
)
```

`httpx.post` does not return until the server has finished writing the entire
response body. The model generates its answer one token at a time, over
seconds, and the server holds every one of those tokens until the last one
exists. Then it sends the lot. Your program is blocked on a single line for
the whole generation and has literally nothing to display, because it has
received nothing.

This is not a performance problem. Streaming does not make the model faster.
The total time from your key press to the final word is the same either way.
What changes is that the first word appears almost immediately instead of at
the end, and a program that shows progress feels alive while a program that
shows nothing feels broken. That difference in feel is the whole reason every
chat product you have ever used types its answer out at you.

There is a second reason, less obvious and more practical. When output
arrives progressively, you can act on it progressively. You can print it, log
it, scan it for a stop phrase, or cut the connection when the model starts
going somewhere useless. None of that is possible when the first thing you
learn about the answer is that it is finished.

## 2. What server sent events are and how to read one by eye

Server sent events, usually shortened to SSE, is the format providers use to
send you a response in pieces. It is a text format carried over an ordinary
HTTP response body, and it is small enough to describe completely in one
section.

### The rules of the format

A stream is a sequence of events. An event is one or more lines, and a blank
line ends the event. A line that starts with `data: ` carries the payload,
and everything after that six character prefix is the payload text. Lines
starting with other prefixes exist in the wider standard, such as `event: `
and `id: `, and none of the providers we care about use them here. Anything
you do not recognise you skip.

That is the entire specification you need. Here is a real fragment, exactly
as this project's fake server writes it when you ask the model to say hello.

```text
data: {"choices": [{"index": 0, "delta": {"content": "Hello "}}]}

data: {"choices": [{"index": 0, "delta": {"content": "from t"}}]}

data: {"choices": [{"index": 0, "delta": {"content": "he moc"}}]}

data: {"choices": [{"index": 0, "delta": {"content": "k serv"}}]}

data: {"choices": [{"index": 0, "delta": {"content": "er."}}]}

data: {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}

data: [DONE]

```

Read those blank lines. They are not formatting for your comfort, they are
the separator that says one event has ended and another may begin. The server
writes them on purpose. You can see it doing so in `mock_server.py`.

```python
for event in events:
    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
    self.wfile.flush()
self.wfile.write(b"data: [DONE]\n\n")
```

The `\n\n` is the line ending of the data line followed by the blank
separator line. The `flush` is what makes this streaming rather than
buffering, because without it the operating system would happily hold the
bytes until it had a comfortable amount to send.

### The pieces inside the payload

Now look at what is inside a single event.

```json
{"choices": [{"index": 0, "delta": {"content": "Hello "}}]}
```

Compare that with the non streaming body you parsed in lesson 03.

```json
{"choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello from the mock server."}}]}
```

Two differences and only two. The key is `delta` rather than `message`, and
its value is a fragment rather than the whole thing. The outer wrapper is
identical, which is deliberate on the provider's part and convenient for us,
because `json.loads(data)["choices"][0]` means the same thing in both worlds.

Notice that the fragments are not words. `"from t"` cuts the word "the" in
half. Streaming carries whatever the tokeniser produced, and token boundaries
have nothing to do with word boundaries. If you ever write code that assumes
a fragment is a word, or that fragments end at spaces, it will work for a
week and then embarrass you.

### The last two events

The second to last event is the one with an empty delta.

```text
data: {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
```

Nothing new arrived. The provider is telling you why generation stopped.
`stop` means the model finished a sentence and chose to end. `tool_calls`
means it ended because it wants a tool run. `length` means it hit the output
token limit and was cut off, which becomes very important in section 6.

The final event is the sentinel.

```text
data: [DONE]
```

That payload is not JSON. It is the four characters `[DONE]` and nothing
else. If you hand it to `json.loads` you get an exception, which is a rite of
passage every person writing their first streaming client goes through. It
exists because a stream needs an explicit end marker that is distinguishable
from a dropped connection. Without it, a client that stopped receiving bytes
could not tell "the model finished" apart from "your wifi died", and those
two situations call for very different behaviour.

### Why this format and not websockets

The obvious question is why providers did not just use websockets, which
everybody has heard of and which are built for pushing data at a client.
Three reasons, and they all point the same way.

First, this traffic only goes one direction. You send a request, the server
sends an answer in pieces, done. Websockets give you a full duplex channel
where both sides can talk at any time. You would be paying for a capability
you never use.

Second, this is a plain HTTP response. The status line, the headers, the
bearer token, and the body all work exactly as they do for any other request.
That means every proxy, load balancer, corporate firewall, CDN, and HTTP
library on earth already handles it. Websockets need an upgrade handshake
that a surprising amount of network infrastructure blocks or mangles, and
they need library support your language may or may not have.

Third, it needs no extra protocol on top. Look again at what you have to
implement to consume it. Split on newlines, keep lines starting with a
prefix, stop on a sentinel. That is a dozen lines of code with no dependency.
A websocket client is a dependency, a handshake, a framing layer, a ping and
pong keepalive, and a reconnection story.

The trade is that you cannot send anything to the server once the request is
in flight. Since you have nothing to send, that trade costs you nothing.

## 3. Part one, streaming text

Now open `llm.py` and read the first half of the function. The signature
changed.

```python
def complete_stream(messages, tools=None, on_text=None):
    """Stream one reply. Returns (text, tool_calls).

    on_text is called with every piece of text as it arrives.
    """
```

It is a new name rather than an edit to `complete`, so you can put lesson 04
and lesson 05 side by side and diff them. There is one new parameter,
`on_text`, and we will come back to it in a moment.

The environment variables, the headers, and the bearer token are byte for
byte the same as lesson 03 and lesson 04. Only one line of the request
changes.

```python
payload = {"model": model, "messages": messages, "stream": True}
```

That single key is what turns the response from one JSON document into an SSE
stream. It is a request for a different response format, nothing more. The
model, the prompt, and the tools are all unchanged, and the answer you
eventually assemble is the same answer.

### The stream context manager

Here is the shape of the reading code.

```python
with httpx.Client(timeout=120) as client:
    with client.stream(
        "POST", f"{base_url}/chat/completions", json=payload, headers=headers
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            ...
```

Three things are going on and each deserves a sentence.

`httpx.Client` is a connection pool with a lifetime. The convenience function
`httpx.post` you used in lesson 04 creates one of these internally for a
single request and throws it away. When you are going to hold a connection
open while reading from it, you want the object in scope, so we create it
explicitly and let the `with` block close it.

`client.stream` is the important change. Where `httpx.post` returns after the
body has been fully downloaded, `client.stream` returns as soon as the status
line and headers have arrived, with the body still open and still arriving.
It has to be used as a context manager, because there is now an open socket
that somebody must close whether your loop finishes normally, breaks early,
or raises. The `with` block is that somebody. If you try to use the response
after the block ends, httpx will tell you the stream is closed, and it is
right to.

`response.raise_for_status()` still works here because the status code
arrived with the headers, before any body. A 401 or a 500 is caught before
you waste time parsing fragments of an error page.

`response.iter_lines()` is a generator. Every time the loop asks it for a
value it hands over the next complete line that has arrived, decoded from
bytes to `str` and with the trailing newline stripped. When nothing has
arrived yet it blocks and waits. When the body ends it stops. The blank
separator lines come through as empty strings, which is convenient, because
an empty string does not start with `data: ` and our filter drops it without
a special case.

### The body of the loop

```python
for line in response.iter_lines():
    if not line.startswith("data: "):
        continue
    data = line[len("data: ") :]
    if data == "[DONE]":
        break
    delta = json.loads(data)["choices"][0].get("delta", {})
```

Line by line.

The `startswith` guard throws away blank separator lines, any comment or
keepalive line a provider might send, and anything else we do not understand.
Being liberal about what you skip is what keeps this code working across
providers that each add their own decoration.

The slice `line[len("data: ") :]` strips the six character prefix. Writing
`len("data: ")` rather than the number 6 means nobody has to count characters
to check the code, and nobody accidentally leaves the leading space on the
payload.

The `[DONE]` check comes before the parse, not after. This is the whole
defence against the exception mentioned in section 2, and its position in the
function is the entire trick.

`.get("delta", {})` rather than `["delta"]` because the final event before
`[DONE]` carries `finish_reason` and may carry no delta at all, or an empty
one. Reaching for a key that is not there would raise on the second to last
event of a perfectly successful stream, which is a maddening bug to find.

### Accumulating and calling back at the same time

```python
if delta.get("content"):
    text_parts.append(delta["content"])
    if on_text:
        on_text(delta["content"])
```

Every piece of text is doing two jobs, and this is worth being explicit about
because it looks redundant on first reading.

The `text_parts.append` is the accumulation. At the end of the function,
`"".join(text_parts)` rebuilds the complete answer. We need that because the
answer has to go back into `messages` as the content of the assistant turn.
The conversation history is not a stream, it is a list of whole messages, and
the model on the next turn must see the full text of what it said last time.
Storing thirty fragments would be storing the transport's business as if it
were the conversation's business.

The `on_text` call is the delivery. It hands each piece to whoever asked for
it the moment it exists. In `agent.py` that caller is a one line lambda.

```python
text, calls = complete_stream(
    messages, tools.SCHEMAS, on_text=lambda piece: print(piece, end="", flush=True)
)
```

`end=""` because the fragments already contain whatever newlines belong in
the answer, and `flush=True` because Python buffers standard output and would
otherwise sit on your beautifully streamed text until the line was complete,
undoing the entire lesson.

Now, why a callback rather than making `complete_stream` a generator that
yields pieces? Both designs work and real libraries ship both. The callback
wins here for a specific reason. A generator would have to yield two
different kinds of thing, text fragments during the stream and a list of tool
calls at the end, and the caller would need to sort them out. That pushes
protocol knowledge up into `agent.py`, which is exactly where we do not want
it. With a callback, `complete_stream` keeps its lesson 04 return type of
`(text, calls)`, the agent loop keeps its shape, and the streaming is an
optional side channel you can ignore entirely by passing nothing. Look at
`check.py` for proof that ignoring it is fine.

```python
_, calls = complete_stream([{"role": "user", "content": PROMPT}], tools.SCHEMAS)
```

No `on_text`, no printing, same return value. Two callers with different
needs, one function, no branching.

### Proving the pieces add up

The first half of `check.py` tests exactly the property that matters.

```python
pieces = []
text, _ = complete_stream(
    [{"role": "user", "content": "Say hello."}], None, on_text=pieces.append
)
if len(pieces) < 2:
    print(f"FAIL the reply did not arrive in pieces. Got {len(pieces)} piece(s)")
    sys.exit(1)
if "".join(pieces) != text:
    print("FAIL the streamed pieces do not add up to the final text")
    sys.exit(1)
print(f"OK text arrived in {len(pieces)} pieces")
```

Passing `pieces.append` as the callback is a neat trick worth stealing. A
list's own bound method is already a function of one argument that records
what it was given, so you get a recorder without writing one.

The two assertions are the two ways streaming can betray you. Fewer than two
pieces means you did not really stream, you just received a whole answer in
one event and never exercised the accumulation. Pieces that do not join back
into the returned text means you dropped or duplicated something, which is
the failure that produces answers with a missing word in the middle.

Run it and you get this.

```text
OK text arrived in 5 pieces
```

Five, because the fake server slices its greeting into six character chunks.
You saw those five chunks in section 2.

## 4. Part two, streaming tool calls

This is the hard half. Everything up to here has been bookkeeping. What
follows is the part where the obvious approach is wrong and the reason is not
obvious.

### The thing that breaks the obvious approach

In lesson 03 a tool call arrived as one object with a complete arguments
string.

```json
{
  "id": "call_mock_1",
  "type": "function",
  "function": {"name": "add", "arguments": "{\"a\": 2, \"b\": 3}"}
}
```

You learned there that `arguments` is a string containing JSON rather than an
object, and that `json.loads` turns it into a dictionary. Fine.

Streaming takes that string and cuts it into pieces, because the model
produced it token by token exactly like it produces prose. Here is the real
stream for `add` with `a` equal to 2 and `b` equal to 3, copied from this
project's fake server, which slices tool arguments into five character
chunks.

```text
data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "id": "call_mock_1", "type": "function", "function": {"name": "add", "arguments": ""}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\"a\":"}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": " 2, \""}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "b\": 3"}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "}"}}]}}]}

data: {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}

data: [DONE]

```

Stare at the first event. It carries the `id`, the `type`, the `name`, and an
`arguments` value of the empty string. That is the announcement. The provider
is telling you a tool call is starting, here is who it is, the body follows.

Now stare at the four events after it. They carry no `id` and no `name`, only
a further slice of `arguments`. Strip away the JSON envelope and the actual
argument text arrives like this.

```text
piece 1   {"a":
piece 2    2, "
piece 3   b": 3
piece 4   }
```

Those are the real fragments, with the escaping of the wire format removed.
Now try to do the sensible looking thing with them.

```python
arguments = json.loads(piece)   # do not do this
```

Every single one fails.

```text
json.loads('{"a":')   -> JSONDecodeError: Expecting value: line 1 column 6 (char 5)
json.loads(' 2, "')   -> JSONDecodeError: Extra data: line 1 column 3 (char 2)
json.loads('b": 3')   -> JSONDecodeError: Expecting value: line 1 column 1 (char 0)
json.loads('}')       -> JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

Look at piece 2 and piece 3 particularly, because piece 2 shows the most
dangerous version of this failure. The fragment ` 2, "` starts with a
perfectly good JSON number, so the parser reads the `2`, decides it has a
complete document, and then complains about the `, "` that follows. A
slightly different fragment would have parsed cleanly and handed you the
number 2 as though that were the answer, which is a silent wrong result
rather than a loud error. Piece 3 is the mirror image. It begins with the
letter `b`, which is not the key `b` but a character inside a string that
opened in the previous event. There is no possible parser that can do
something correct with `b": 3` alone.

This is the mental model that unlocks the section. **The stream is not
carrying JSON values. It is carrying the characters of a string, and the
string happens to contain JSON once it is complete.** Concatenation is the
only operation defined on it. Parsing is a thing you may do once, at the end.

### The accumulate then parse pattern

Here is the tool call half of the loop in `llm.py`.

```python
for chunk in delta.get("tool_calls", []):
    index = chunk.get("index", 0)
    slot = partial.setdefault(index, {"id": "", "name": "", "arguments": ""})
    if chunk.get("id"):
        slot["id"] = chunk["id"]
    function = chunk.get("function", {})
    if function.get("name"):
        slot["name"] = function["name"]
    if function.get("arguments"):
        slot["arguments"] += function["arguments"]
```

Read it as three separate ideas.

**A buffer that exists before the data does.** `partial` is a dictionary
declared next to `text_parts` at the top of the function. `setdefault` either
returns the existing entry for this index or creates a fresh one with three
empty strings and returns that. It means the announcement event and the
fragment events run through identical code with no "is this the first one"
branch. Empty string is the right zero value here, because empty string is
what you get when you have concatenated nothing.

**Fields that overwrite, and a field that appends.** `id` and `name` are
assigned with `=`, arguments are appended with `+=`. That asymmetry is the
whole design. The identity of a call arrives once and completely. Its
arguments arrive many times and partially. The `if chunk.get("id")` guard
exists because later events omit `id` entirely, and blindly assigning would
overwrite a good identifier with `None`.

**No parsing anywhere in the loop.** Not one `json.loads` touches
`slot["arguments"]` while the stream is running, because as you just proved,
there is nothing valid to parse.

Now the parse, which happens after the `with` blocks have closed and the
stream is finished.

```python
calls = []
for _, slot in sorted(partial.items()):
    try:
        arguments = json.loads(slot["arguments"] or "{}")
        error = ""
    except json.JSONDecodeError as problem:
        arguments = {}
        error = f"arguments were not valid JSON ({problem})"
    calls.append(
        {
            "id": slot["id"],
            "name": slot["name"],
            "arguments": arguments,
            "error": error,
        }
    )
return "".join(text_parts), calls
```

`sorted(partial.items())` because dictionaries preserve insertion order and
we want index order, and those are the same only when the provider was tidy.
Sorting by the index the provider gave us costs nothing and removes a class
of bug that would appear only against one particular endpoint.

The `or "{}"` is inherited from lesson 03 and handles a tool that takes no
arguments, where the provider sends nothing at all rather than an empty
object.

The `try` block is new, and it is the subject of section 6. Set it aside for
one more section.

Notice what this pattern buys you overall. Both halves of the function follow
the same rule. Fragments go into a buffer during the stream, meaning is
extracted after the stream. The text half joins a list, the tool call half
concatenates a string and then parses it. It is one idea wearing two hats,
and once you see it that way the function stops looking like two unrelated
loops.

## 5. Why the buffer is keyed by index

You could ask a fair question about the code above. There is one tool call in
the example, so why is `partial` a dictionary at all? Why not a single string
variable that you keep adding to?

Because a model is allowed to ask for several tools in one turn, and it does.
"Roll a dice and add 10 to the result" is one turn with one tool. "Roll a
dice and also tell me what 2 plus 3 is" is one turn with two, and a
reasonable model will ask for both at once rather than waste a round trip.
Lesson 04 already loops over `calls` for exactly this reason.

When there are two calls, every fragment event carries an `index` saying
which call it belongs to. Here is what the fake server sends for `add` with
`a` equal to 2 and `b` equal to 3 alongside `roll_dice` with `sides` equal to
6.

```text
data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "id": "call_mock_1", "type": "function", "function": {"name": "add", "arguments": ""}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\"a\":"}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": " 2, \""}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "b\": 3"}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "}"}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 1, "id": "call_mock_2", "type": "function", "function": {"name": "roll_dice", "arguments": ""}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 1, "function": {"arguments": "{\"sid"}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 1, "function": {"arguments": "es\": "}}]}}]}

data: {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 1, "function": {"arguments": "6}"}}]}}]}

data: {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}

data: [DONE]

```

Be careful not to confuse the two `index` fields. The outer one, next to
`delta`, is the choice index and is always 0 unless you asked the provider
for several alternative completions. The inner one, inside the `tool_calls`
list, is the one that matters here. It says which of this turn's tool calls
the fragment belongs to.

Our fake server is polite and finishes call 0 before starting call 1. Real
providers are not obliged to be, and some are not. The fragments of two calls
can interleave, because the model is producing one token stream and the
provider is forwarding it, and the ordering you receive is the ordering the
model happened to produce.

An interleaved stream would carry argument fragments in this order.

```text
index 0   {"a":
index 1   {"sid
index 0    2, "
index 1   es": 
index 0   b": 3
index 1   6}
index 0   }
```

Now imagine you had used one string variable and appended everything to it.

```python
buffer = ""      # the design that cannot work
buffer += piece
```

You would end up holding this.

```text
{"a":{"sid 2, "es": b": 36}}
```

That is not broken JSON that a smarter parser could rescue. It is two
different documents shuffled together like two halves of a deck of cards. The
information about which character belonged to which call was thrown away the
moment you appended without looking at the index, and no amount of cleverness
afterwards recovers it.

Keying the buffer by index is what keeps the two streams apart.

```python
slot = partial.setdefault(index, {"id": "", "name": "", "arguments": ""})
```

Index 0 accumulates into its own slot, index 1 into its own, and neither one
ever sees the other's characters. At the end you have two complete strings
that each parse cleanly.

There is a wider lesson here that outlives this file. When a protocol hands
you an identifier alongside a fragment, the identifier is not decoration. It
is there because the fragments can arrive out of order, and the protocol
designer knew it even if the example you were reading did not show it. Code
that ignores such an identifier works right up until the day the ordering
changes, and then fails in a way that looks like the model went insane rather
than like your buffer got shuffled.

And the reason our fake server does not interleave is worth saying plainly.
A deterministic test server should reproduce the shape of real traffic, not
its worst day. The index handling is correct anyway, so it is ready when a
real provider does interleave, and you will not be debugging it at that
point.

## 6. When the JSON never finishes

Everything in section 4 assumed the last fragment eventually arrives. Now
consider what happens when it does not.

Every model has an output token limit. Sometimes it is a provider default,
sometimes it is a `max_tokens` value that you set yourself, sometimes it is
the model reaching the end of its context window. When generation hits that
ceiling, the provider stops the model mid word and closes the stream. It is
not an error. The HTTP status is 200, the SSE stream is well formed, the
`[DONE]` sentinel arrives exactly as it should. The `finish_reason` field on
the second to last event says `length` instead of `stop` or `tool_calls`,
which is your only hint.

If that happens during prose, you get a sentence that stops mid word and a
human notices. If it happens during a tool call, you get this in your buffer.

```text
{"a": 2, "b
```

The characters stopped. There is no closing quote, no value for `b`, no
closing brace. And `json.loads` says so.

```text
json.JSONDecodeError: Unterminated string starting at: line 1 column 10 (char 9)
```

Depending on where the cut landed you get a different complaint, and all
three of these are ordinary.

```text
'{"a": 2, "b'    -> Unterminated string starting at: line 1 column 10 (char 9)
'{"a": 2, '      -> Expecting property name enclosed in double quotes: line 1 column 10 (char 9)
'{"a": 2, "b": ' -> Expecting value: line 1 column 15 (char 14)
```

### The worst possible response, and why people write it

The tempting fix is one line, and versions of it are sitting in real
codebases right now.

```python
try:
    arguments = json.loads(slot["arguments"] or "{}")
except json.JSONDecodeError:
    arguments = {}          # never do only this
```

It stops the crash. It is the worst available behaviour, and it is worth
naming all three of its failure modes because each one is nastier than the
last.

**The tool runs with no arguments.** `tools.run("add", {})` becomes `add()`,
which raises `TypeError: add() missing 2 required positional arguments`. Here
that is caught and turned into a harmless error string, because `add` is a
toy. Now put a real tool in its place. `delete_files()` with no arguments,
where the parameter that never arrived was the filter restricting it to
temporary files. `send_email()` where the missing parameter was the
recipient. `transfer(amount)` where the amount defaulted to something. A
truncated argument list turns a specific instruction into a general one, and
general instructions to destructive tools are how disasters read in the
incident report.

**The model never learns it made a mistake.** This one is subtler and, in
practice, worse. The model asked for `add` with two arguments. Something
downstream quietly rewrote the request to `add` with zero arguments. Whatever
comes back, the model sees a result to a question it did not ask. It cannot
correct an error it was never told about. The single most valuable property
of the agent loop you built in lesson 04 is that the model reads the
consequences of its own actions and adapts. Swallowing an error severs
exactly that feedback, and you are left with a model that appears to be
behaving stupidly for no reason.

**The broken call repeats forever.** Remember that the conversation is
replayed in full on every turn. The malformed call goes into `messages` as
part of the assistant turn, and it stays there for the rest of the run. On
the next turn the model reads a history in which it apparently asked for
`add` with no arguments and got a strange result, and the most likely
continuation of that history is more of the same. You have written a bad
example into the model's own context and then asked it to continue the
pattern. This is how agents get stuck in a loop that burns through
`max_turns` and real money while doing nothing.

### What this lesson does instead

`llm.py` records the failure rather than hiding it.

```python
except json.JSONDecodeError as problem:
    arguments = {}
    error = f"arguments were not valid JSON ({problem})"
```

The empty dictionary is a placeholder that keeps the shape of the returned
record consistent. It is never the thing that gets executed, because the
`error` string travels with it and `agent.py` checks that string first.

```python
for call in calls:
    if call["error"]:
        result = f"Error: {call['error']}. Send the tool call again."
        print(f"\n[{call['name']} was not run because {call['error']}]")
    else:
        print(f"\n[calling {call['name']} with {call['arguments']}]")
        result = tools.run(call["name"], call["arguments"])
        print(f"[{call['name']} returned {result}]")
    messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
```

Three properties fall out of those seven lines.

The tool does not run. No side effect happens on the strength of arguments we
know are incomplete.

A `tool` message still gets appended, with the matching `tool_call_id`. This
is not optional politeness. Providers require that every tool call in an
assistant turn is answered by a tool message with the same id, and a missing
one is a 400 on your next request. An error is a perfectly good answer.

The content of that message is readable English describing what went wrong,
followed by an instruction about what to do next. The model reads it on the
following turn exactly as it reads any other tool result, and the usual
outcome is a corrected second attempt. That works because a model that
receives "arguments were not valid JSON" plus a prompt to retry has enough to
act on, whereas a model that receives silence has nothing.

This is the same principle as `tools.run` catching every exception and
returning a string, which you met in lesson 03. Failures become text, text
goes into the conversation, and the model gets to respond to reality. An
agent that can read its own error messages is enormously more capable than
one that cannot, and both of these small pieces of code exist to keep that
channel open.

### Why lesson 03 had none of this

Go back and look at the line you wrote two lessons ago.

```python
"arguments": json.loads(raw["function"]["arguments"] or "{}"),
```

No `try`. No `except`. Nothing. If the model had produced malformed
arguments, that line would have thrown a `JSONDecodeError` straight up
through `complete` and out of the program with a traceback.

That was on purpose, and it is worth being straight with you about why,
because it is a teaching decision you will meet again in this course.

At the time, there was no reason to make the line complicated. The arguments
arrived as one complete string in one response, and the only way that string
could be broken was a weak model producing genuine nonsense, which is rare
enough that a traceback is a fine outcome. Adding a `try` block would have
been a guard against a problem that had not yet appeared, sitting in the
middle of the exact three lines the reader was supposed to be studying. The
lesson 03 README even says so at the end of the section, promising that a
real agent would catch it and feed the error back. This is that promise
coming due.

What changed in lesson 05 is not the code style. It is the world. Truncation
is not rare when arguments are streamed, because a stream can be cut at any
character, and the cut lands mid arguments often enough that you will see it
on a real model within a day of running an agent with a low token budget. The
error handling arrived at the moment the error became likely.

And there is a reason to do it in this order rather than protecting
everything from the start. You now know what a `JSONDecodeError` from a
truncated tool call actually looks like, what its message says, and where it
comes from. If lesson 03 had wrapped that line in a `try` before you had ever
met the exception, the `try` would have been noise you copied. Seeing
something break and then fixing it teaches better than being handed a guard
against a problem you have never had. Defensive code you do not understand is
just clutter that makes you feel safe.

### Watch it happen yourself

You should see this rather than take it on faith. It needs a real model,
because the fake server always sends complete arguments by construction.

Open `llm.py` and add a deliberately cruel token limit to the payload.

```python
payload = {"model": model, "messages": messages, "stream": True, "max_tokens": 12}
if tools:
    payload["tools"] = tools
```

Point at a real endpoint and run the agent.

```bash
cd lessons/05-streaming
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=qwen2.5:7b
python agent.py
```

On Windows PowerShell.

```powershell
cd lessons\05-streaming
$env:AGENTPATH_BASE_URL = "http://localhost:11434/v1"
$env:AGENTPATH_MODEL = "qwen2.5:7b"
python agent.py
```

Twelve tokens is not enough to finish a tool call, so the stream gets cut
part way through the arguments and you see something close to this.

```text
[add was not run because arguments were not valid JSON (Unterminated string starting at: line 1 column 10 (char 9))]
```

The agent then sends the error back, the model tries again, and gets cut off
again, and this repeats until `max_turns` runs out and you get the
`RuntimeError`. That looping is not a bug in the recovery, it is what a
genuinely impossible situation looks like. The budget is too small for any
correct answer to exist.

Try 12, then 40, then 200, and watch where the cut lands each time. Then put
the line back the way it was. If you want to inspect the raw fragments while
you are in there, drop a print inside the loop.

```python
if function.get("arguments"):
    print(repr(function["arguments"]))
    slot["arguments"] += function["arguments"]
```

Seeing your own model's real fragments scroll past, with their odd
boundaries, is worth more than any diagram of the format.

## 7. Why we rebuilt the loop now instead of later

A reasonable objection to this whole chapter is that streaming is cosmetic.
The agent worked at the end of lesson 04. Streaming makes it feel nicer.
Surely that is a polish task for after the interesting features are built.

That reasoning is wrong, and the specific way it is wrong is worth
understanding, because it applies well beyond this course.

Streaming is not a setting. It changes the shape of the code. Count what
actually moved between the two versions of `llm.py`.

```text
lesson 04                          lesson 05
one request, one response          one request, many events
parse a whole document             filter lines, parse each payload
read message.content               concatenate content deltas
read message.tool_calls            accumulate fragments keyed by index
arguments already complete         arguments complete only at the end
function returns a value           function also emits values as it runs
no failure mode for arguments      truncation is a normal outcome
```

Every one of those is a change to control flow or to the contract of the
function, not to a parameter. The return type happens to have stayed
`(text, calls)`, and that was a deliberate effort to contain the blast
radius, not a happy accident.

Now picture doing this retrofit later. By the end of part 2 the codebase has
several tool implementations, a confirmation gate that pauses before running
anything dangerous, a system prompt, and, one part later, a conversation store. Every one of
those touches the boundary between "the model produced something" and "the
program did something", and that boundary is precisely what streaming
redraws. You would be rewriting the printing, the logging, the confirmation
prompt, and the tests all at once, in a codebase where you can no longer see
the whole path in one screen. That is a week of work and a large diff instead
of an afternoon and a small one.

The general principle is that changes to the shape of your data flow should
be made when the program is small. Cost grows with the amount of code built
on top of the old shape. Streaming, retries, cancellation, and structured
logging are all in this family. They look like polish, they behave like
foundations, and a project that defers all four ends up rewriting its core
after it has users.

There is a second, quieter benefit. Because `complete_stream` returns the
same `(text, calls)` pair as `complete`, `agent.py` is almost unchanged
between lessons 04 and 05. The diff is the `on_text` lambda, the `print()`
that ends the streamed line, and the error branch from section 6. That is
what a well placed boundary earns you. The transport got radically more
complicated and the loop above it barely noticed, which is the same idea
lesson 06 takes considerably further.

## 8. Troubleshooting

### The stream works but tool calls come back empty

Some endpoints, particularly local ones, support streaming and support tool
calling, but not at the same time. The request succeeds, prose streams
beautifully, and `tool_calls` never appears in any delta. Depending on the
server you may instead get a 400 the moment `stream` and `tools` are both in
the payload, or a tool call delivered as literal text inside `content`.

Confirm it in one step. Run `check.py` and read which assertion failed.

```text
OK text arrived in 5 pieces
FAIL streamed tool arguments were not reassembled. Got []
```

Text streaming passed, tool calls came back as an empty list. If that is what
you see, the fix is to stop asking for a stream whenever tools are present.

```python
    want_stream = not tools
    payload = {"model": model, "messages": messages, "stream": want_stream}
    if tools:
        payload["tools"] = tools
```

Then handle the non streaming reply, since the body is now one JSON document
rather than a sequence of events.

```python
    if not want_stream:
        response = httpx.post(
            f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        text = message.get("content") or ""
        if text and on_text:
            on_text(text)
        calls = []
        for raw in message.get("tool_calls") or []:
            try:
                arguments = json.loads(raw["function"]["arguments"] or "{}")
                error = ""
            except json.JSONDecodeError as problem:
                arguments = {}
                error = f"arguments were not valid JSON ({problem})"
            calls.append(
                {
                    "id": raw["id"],
                    "name": raw["function"]["name"],
                    "arguments": arguments,
                    "error": error,
                }
            )
        return text, calls
```

That block goes immediately before the `with httpx.Client(...)` line, and the
streaming path below it is untouched.

Notice that `on_text` is still called, once, with the whole text. The
callback contract does not promise small pieces, only that you will receive
the text as it becomes available. Here it becomes available all at once.
`agent.py` needs no change, `check.py`'s tool assertions still pass, and only
the "arrived in 5 pieces" assertion is affected, which it will not be because
that call passes no tools.

This is a real trade and you should make it knowingly. You lose the live feel
on turns where the model is choosing a tool, which is often the slowest turn.
You keep it on the final turn where the model writes the answer to the user,
which is the turn where waiting is most visible. If your endpoint forces the
choice, that is the right half to keep.

### JSONDecodeError on the very last event

```text
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

You parsed `[DONE]`. The sentinel check has to come before `json.loads`, not
after it and not inside a `try`. Check the order in section 3.

### Text appears all at once at the end

Two candidates. Either you dropped `flush=True` from the print, in which case
Python is buffering your output and releasing it when the process exits, or
something between you and the provider is buffering the response. An
aggressive corporate proxy will happily collect the whole SSE body and
deliver it in one lump, which is a network problem rather than a code one.
Test against the fake server first to find out which side the problem is on.

```bash
python ci/run_lessons.py
```

### Only one piece arrives

```text
FAIL the reply did not arrive in pieces. Got 1 piece(s)
```

The reply was short enough to fit in one event, or the endpoint ignored
`stream` and sent a normal JSON body, in which no line starts with `data: `. Confirm by printing every line the loop sees.

```python
for line in response.iter_lines():
    print(repr(line))
```

If you see one long line of JSON with a `message` key rather than several
short ones with `delta` keys, your endpoint ignored the `stream` flag.

### The tool result never matches its call

```text
400 Bad Request  ... 'tool_call_id' did not match any tool call
```

An `id` got lost. The usual cause is dropping the `if chunk.get("id")` guard
so that a later fragment, which carries no id, overwrote the good one with
`None`. Section 4 covers why that guard is there.

### KeyError on an environment variable

```text
KeyError: 'AGENTPATH_BASE_URL'
```

The variable is not set in this shell. Setting it in one terminal does not
set it in another. Same as every previous lesson.

## 9. What you cannot do yet

Run the check one more time and enjoy it, because you have earned it.

```text
OK text arrived in 5 pieces
OK streamed tool arguments were reassembled into valid JSON

[calling add with {'a': 2, 'b': 3}]
[add returned 5]
The tool returned 5.
OK the streaming agent completed the tool round trip
```

The last line is a full agent turn, streamed, with a tool call whose
arguments were assembled from four fragments that were individually
unparseable. That is a real streaming client and you wrote all of it.

Now open `llm.py` and read it with a suspicious eye, looking for anything
that would break if you changed provider.

```python
delta = json.loads(data)["choices"][0].get("delta", {})
delta.get("content")
delta.get("tool_calls", [])
chunk.get("index", 0)
chunk["function"]["arguments"]
```

Every one of those is a shape decision made by OpenAI. The word `choices`,
the word `delta`, arguments being a string rather than an object, the index
living where it lives. Nothing about streaming requires any of it. They are
one company's answer to a set of questions, copied by everybody who wanted
their endpoint to work with existing client libraries.

Anthropic answered the same questions differently, and this project's fake
server can speak that dialect too, which lets you compare them side by side.
Here is the same `add` call in Anthropic's streaming format.

```text
data: {"type": "message_start", "message": {"id": "mock-1", "role": "assistant", "content": []}}

data: {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "call_mock_1", "name": "add", "input": {}}}

data: {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "{\"a\":"}}

data: {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": " 2, \""}}

data: {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "b\": 3"}}

data: {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "}"}}

data: {"type": "content_block_stop", "index": 0}

data: {"type": "message_delta", "delta": {"stop_reason": "tool_use"}}

data: {"type": "message_stop"}

```

Look at what survived the translation and what did not. The transport is
identical, still `data: ` lines with blank separators. The argument fragments
are character for character the same, still five character slices of the same
string, still individually unparseable, still needing accumulate then parse.
The index is still what keeps concurrent calls apart.

Everything else is different. Events carry a `type` field and six kinds of them appear in this one
stream. There is no `choices` list. A tool call is a content block
that starts and stops rather than an entry in a `tool_calls` array. The
fragments live under `partial_json` inside a `delta` with its own `type`. The
stream ends with `message_stop` rather than `[DONE]`, so a client that
`break`s on the sentinel would hang waiting for one that never comes.

`llm.py` understands exactly none of that. Change `AGENTPATH_BASE_URL` to an
Anthropic endpoint and it fails immediately, on the first event, with a
`KeyError` for `choices`.

That is the limit of this code. It is welded to one company's response shape,
in a file that is also doing the environment reading, the HTTP call, the line
filtering, the buffering, and the parsing. To support a second provider you
would have to interleave a second set of shape decisions through all of that,
and the ideas you actually care about, accumulate then parse and key by
index, would be buried under `if provider ==` branches.

The fix is to notice that those ideas are not provider specific at all. Every
provider streams. Every one of them sends tool arguments as fragments. Every
one of them needs the fragments kept apart by some identifier. What differs
is only where each field sits in the JSON. Pull the shape knowledge into one
place per provider, keep one common representation for the rest of the
program, and `agent.py` stops caring who is answering the phone.

That is lesson 06.
