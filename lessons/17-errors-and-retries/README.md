[อ่านภาษาไทย](README.th.md)

# Lesson 17. Errors and retries

Every chapter up to here has been written as though the network always answers,
the model always makes progress, and the person at the keyboard never changes
their mind. None of those three things is true, and the gap between them and
reality is the whole subject of this chapter.

This is the last mechanism chapter of part 3. What it adds is small, ninety
eight lines across two new files, and what it prevents is the difference between
a program you demo and a program you leave running while you make coffee.

Files in this folder.

```text
lessons/17-errors-and-retries/
  retry.py       new. which failures are worth retrying, and how long to wait
  cancel.py      new. one object that says stop
  agent.py       the loop, now consulting a cancellation token in two places
  providers.py   lesson 15's providers, now opening the stream through retry
  tools.py       lesson 16's tools, plus a cancellation check in run_shell
  permissions.py unchanged since lesson 12
  session.py     unchanged since lesson 13
  context.py     unchanged since lesson 14
  usage.py       unchanged since lesson 15
  retrieval.py   unchanged since lesson 16
  prompt.py      unchanged since lesson 10
    grep_worker.py unchanged since lesson 09
  check.py       six claims about failure, proved against the mock server

  README.md      this file
```

`retry.py` is sixty seven lines and `cancel.py` is thirty one. The only edit to
`agent.py` is a new keyword argument and two lines that read it. `providers.py`
gains `open_stream`, which is the one place `with_retries` is wired in, and
`tools.py` gains a cancellation check before a shell command starts. Everything
else in the folder is a byte for byte copy of an earlier lesson, which by now you
should expect and which section 10 finally does something about.

## 1. The problem left over from lesson 16

Lesson 16 finished the retrieval argument and left you with an agent that can
find code by name, by text, and by meaning. It can be pointed at a strange
repository and work out where the relevant file is. It remembers your permission
decisions, writes its conversation to disk, trims itself before it overflows,
counts what it costs, and knows how to search.

It also assumes that nothing goes wrong. Look at what that assumption is doing
in the code.

```python
        text, calls, reported = provider.stream(
            to_send(), schemas, on_text=lambda piece: print(piece, end="", flush=True)
        )
```

There is no `try` anywhere near that line and there never has been. So here is
the list of things that end your run with a traceback.

**A rate limit.** You are on a free tier, or you share a key with three
colleagues, or you asked the agent to read fifteen files and it made fifteen
requests in ninety seconds. The provider answers `429`, `httpx` raises, the
exception travels out of `run` and out of `main`, and the conversation is gone.
The request that failed would have succeeded twenty seconds later.

**A server error.** `500`, `502`, `503`, `529`. A gateway restarting, a model
being rescheduled, a capacity spike that has nothing to do with you. Same
outcome. The provider was briefly unhealthy and your program treated that as
fatal.

**A dropped connection.** Your laptop switches from wifi to a hotspot mid
stream. A corporate proxy closes an idle socket. `httpx` raises a
`ReadError` and everything the agent had learned in that session evaporates.

**A model that gets stuck.** No exception at all. The agent calls `grep_files`
with the same pattern, gets the same empty result, calls it again with a comma
moved, gets the same empty result, and does that until `max_turns` runs out. You
paid for ten turns of nothing and the only signal you got was a `RuntimeError`
at the end saying it stopped after max turns, which is exactly the same thing
you would see if it had been making excellent progress and needed an eleventh.

**A person who changes their mind.** You asked it to refactor the wrong module.
You realise this four seconds in, while it is streaming a plan you no longer
want. You press Ctrl+C. What happens now depends entirely on where the
interpreter was standing when the signal arrived, and none of the possibilities
are good.

Those five failures split into three problems with three different answers.
Failures that fix themselves need retrying, which is sections 2 to 5. A person
who wants to stop needs a way to actually stop, which is section 6. A model
going in circles needs to be told, which is section 7.

The single most important sentence in the chapter is that these three answers
are not interchangeable. Retrying a stuck model wastes money faster. Cancelling
a rate limit throws away a run that would have succeeded. Getting the split
right is most of the work.

## 2. Which failures are worth retrying

Here is the whole of the decision.

```python
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
```

```python
def with_retries(call, attempts=4, sleep=time.sleep):
    """Run call, retrying only the failures that retrying can fix.

    A 400 means the request itself was wrong, so sending the same wrong
    request again produces the same wrong answer more slowly. Only statuses
    that mean try again later, and transport failures, which are safe because
    asking the model again changes nothing, are worth a second attempt.
    """
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except httpx.HTTPStatusError as error:
            if error.response.status_code not in RETRYABLE_STATUS:
                raise
            last_error = error
            if attempt == attempts:
                break
            sleep(delay_for(attempt, error.response))
        except httpx.TransportError as error:
            last_error = error
            if attempt == attempts:
                break
            sleep(delay_for(attempt))
    raise last_error
```

**What it is.** A function that runs another function up to four times, waiting
between attempts, and gives up in a way that preserves the original error.

**Why we are doing it.** Because the majority of failures a real agent meets are
not bugs. They are weather. The provider was busy for a second. The socket
died. Nothing about your program was wrong and nothing about it needs to change.

**Why this way and not another way.** The tempting version is a bare
`except Exception` with a sleep in it, and that version is a disaster, because
it turns every permanent failure into a slow permanent failure. The split
matters more than the mechanism.

### The split, stated plainly

The question is not how bad the error is. The question is whether the same
request, sent again, could produce a different answer.

| Status | Meaning | Retry | Why |
| --- | --- | --- | --- |
| `408` | request timeout | yes | the server gave up waiting, not on the content |
| `409` | conflict | yes | transient contention on the provider side |
| `429` | too many requests | yes | you are early, not wrong |
| `500` | internal server error | yes | something broke over there, not here |
| `502` | bad gateway | yes | a proxy could not reach the backend just then |
| `503` | service unavailable | yes | the service says so in the name |
| `504` | gateway timeout | yes | the backend was slow this once |
| `529` | overloaded | yes | Anthropic's non standard code for exactly this |
| `400` | bad request | **no** | your JSON is malformed or a field is wrong |
| `401` | unauthorized | **no** | your key is wrong and will still be wrong |
| `403` | forbidden | **no** | you do not have access to this model |
| `404` | not found | **no** | that URL or model name does not exist |
| `413` | payload too large | **no** | the conversation is too big and stays too big |
| `422` | unprocessable | **no** | the request parsed and was still invalid |

Read the two halves as two sentences. Everything above the line means try again
later. Everything below the line means the thing you sent was wrong.

That is why `with_retries` handles the two cases with `raise` and `sleep` rather
than with a shared code path. A non retryable status is re-raised immediately,
unwrapped, on the first attempt, so it reaches you in under a second with the
original `httpx` exception intact.

### Why retrying a 400 is worse than not retrying it

It is worth being precise about why the bad half is bad, because the failure it
causes is subtle rather than loud.

Suppose you retried everything. You send a conversation with a tool call whose
result is missing, which is the pairing trap from lesson 14. The provider answers
`400`. You wait one second and send the identical conversation. `400`. You wait
two seconds. `400`. You wait four. `400`.

Seven seconds later you raise the same error you had at time zero. Nothing was
gained. You burned four requests against your rate limit, which makes an actual
`429` more likely for the next real call. And the error you finally show the user
arrives seven seconds after the mistake, by which time they have started reading
something else.

The multiplier is what makes this serious. Four retries per call, on an agent
that makes ten calls per task, is forty pointless requests per broken task. On a
shared key that is enough to rate limit your colleagues out of a service that
was working fine.

A `400` is a bug in your code or in your conversation state. The correct
response to a bug is to see it immediately.

### Why a transport error counts as retryable

This clause deserves its own paragraph because the reasoning is different from
the status code case.

```python
        except httpx.TransportError as error:
            last_error = error
```

`httpx.TransportError` is the base class for every failure where the exchange did
not complete. `ConnectError`, `ConnectTimeout`, `ReadTimeout`, `ReadError`,
`WriteError`, `PoolTimeout`, `RemoteProtocolError`. What they have in common is
the thing that makes them safe.

**Nothing arrived, so nothing happened.** There is no HTTP status because there
is no HTTP response. The request either never reached the server or its answer
never reached you. In both cases the model did not produce anything you have,
and no state on your side changed. Sending it again is not repeating an action,
it is making the action happen for the first time.

Notice the second argument in the transport branch.

```python
            sleep(delay_for(attempt))
```

No response is passed, because there is no response. `delay_for` handles that
with `if response is not None` and falls straight through to the formula. A
server that never answered obviously did not send a `Retry-After` header.

Be honest about the one case where this reasoning is imperfect. A `ReadTimeout`
that happens after the server accepted the request means the work may have
happened and only the answer was lost. For a model call that is harmless,
because the only cost is money and the only state is a conversation you control.
For a tool call it would not be harmless at all, which is section 5.

### Why four attempts

`attempts=4` is a default rather than a law, and the reasoning is arithmetic. With
the delays in the next section, four attempts spans roughly seven seconds in the
worst case. That is long enough to ride out a gateway restart or a burst of rate
limiting, and short enough that a person watching the terminal has not yet
decided the program is hung.

Ten attempts would cover longer outages, and it would also mean a genuinely dead
endpoint takes several minutes to report itself. When a provider is down, finding
out quickly is more valuable than a small chance of surviving it.

## 3. Listening to the server

```python
def delay_for(attempt: int, response=None, base=1.0, cap=30.0) -> float:
    """How long to wait before the given attempt, counting from one.

    A Retry-After header wins outright. It is the server telling us when it
    will be ready, and guessing earlier than that just wastes a request and
    makes the overload worse.
    """
    if response is not None:
        header = response.headers.get("Retry-After")
        if header:
            try:
                return float(header)
            except ValueError:
                pass
    exponential = min(cap, base * (2 ** (attempt - 1)))
    return exponential * (0.5 + random.random() / 2)
```

Read the order of the function. The header is checked first, and if it is
present and parses, the function returns. The formula below it never runs.

**What `Retry-After` is.** A response header, defined in the HTTP specification
and sent by essentially every provider that rate limits you. It carries a number
of seconds. `Retry-After: 2` means come back in two seconds.

**Why we are doing it.** Because it is the only number in this entire chapter
that is not a guess. Our formula is a heuristic invented by us with no knowledge
of the service. The header is the service telling us, from inside, when it will
be ready. When one party to a conversation knows the answer and the other is
estimating, listening is not politeness, it is correctness.

**Why this way and not another way.** The obvious alternative is to treat the
header as advice and take the smaller of the two numbers, on the theory that
coming back early might work and cannot hurt. Both halves of that theory are
wrong.

Coming back early does not work, because the server told you it will not be
ready and it meant it. The early request gets another `429`, so you have spent
an attempt out of your budget of four to learn something you were already told.

And it does hurt. A service that is rate limiting you is under load. Every
request you send while it is shedding load is work it has to do to reject you,
and it is doing that for every client at once. The header is a coordination
mechanism. Ignoring it is defection, and it makes the outage longer for
everybody including you.

### The formula, when the server says nothing

Most failures do not carry a `Retry-After`. A `500` from a crashed worker has no
opinion about the future. That is what the last two lines are for.

```python
    exponential = min(cap, base * (2 ** (attempt - 1)))
```

`attempt` counts from one, so `2 ** (attempt - 1)` gives one, two, four, eight.
The wait doubles each time.

Doubling rather than a fixed delay is the point of the word backoff. A fixed one
second retry sends the same request at the same rate forever, which is the
behaviour of a client that has learned nothing from being told no three times.
Doubling means a service that is briefly busy sees you again quickly, and a
service that is badly broken sees you back off out of its way.

`min(cap, ...)` stops the doubling at thirty seconds. Without it, attempt ten
would wait for over eight minutes, and a wait long enough that the user assumes
the program has hung is worse than a failure they can see.

| attempt | `2 ** (attempt - 1)` | exponential, capped | actual wait after jitter |
| --- | --- | --- | --- |
| 1 | 1 | 1.0 | 0.5 to 1.0 seconds |
| 2 | 2 | 2.0 | 1.0 to 2.0 seconds |
| 3 | 4 | 4.0 | 2.0 to 4.0 seconds |
| 4 | 8 | 8.0 | 4.0 to 8.0 seconds |
| 6 | 32 | 30.0 | 15.0 to 30.0 seconds |

With the default of four attempts you only ever use the first three rows, so the
worst case total wait is seven seconds. The cap exists for callers who ask for
more attempts than the default.

### The try around the float

```python
            try:
                return float(header)
            except ValueError:
                pass
```

`Retry-After` has two legal forms. The seconds form, `Retry-After: 2`, and an
HTTP date form, `Retry-After: Wed, 21 Oct 2015 07:28:00 GMT`. LLM providers send
the seconds form. Proxies, load balancers and corporate gateways sometimes sit in
front of them and send the date form.

`float("Wed, 21 Oct 2015 07:28:00 GMT")` raises `ValueError`, and if that
exception escaped, an unusual header from a middlebox you did not know was there
would crash a function whose entire job is to survive things going wrong. The
`pass` falls through to the formula, which is a worse answer than parsing the
date and a much better answer than a traceback.

## 4. Why jitter is not decoration

```python
    return exponential * (0.5 + random.random() / 2)
```

That multiplier looks like noise for the sake of noise. It is the most important
line in the file and it is worth understanding exactly what it prevents.

**What jitter is.** Randomising each client's wait so that clients which failed
together do not return together. `random.random()` gives a float in `[0.0, 1.0)`,
so `0.5 + random.random() / 2` gives a multiplier in `[0.5, 1.0)`, and the actual
wait is somewhere between half the computed delay and all of it.

**Why we are doing it.** Because without it, a moment of trouble becomes a
sustained outage, and the clients are the ones sustaining it.

### The failure it prevents, step by step

Picture a service with a thousand clients. Something goes wrong for one second
and every request in flight comes back `503`.

Now run the retry logic without jitter, where the wait is exactly one second,
then exactly two, then exactly four.

At time zero, a thousand clients fail. Each computes a delay of exactly 1.0
seconds. At time one, a thousand requests arrive in the same instant.

The service has just come back and is cold. Its caches are empty, its connection
pools are empty, and it now receives its entire daily peak load compressed into
one moment. It falls over again, which it would not have done under the same
thousand requests spread across a second.

So at time one, a thousand clients fail again. Each computes a delay of exactly
2.0 seconds. At time three, a thousand requests arrive in the same instant.

Nothing is breaking this cycle. The service is not recovering because it is
being hit by a synchronised wall of traffic every time it stands up, and the wall
is synchronised precisely because every client is running the same correct
looking retry code. The one second outage is now a minute long, and no client did
anything wrong except being identical to every other client.

That pattern has a name, the thundering herd, and it is one of the classic ways
a distributed system takes itself down without any single component being at
fault.

### What the multiplier does to that

Now put the jitter back. Each client waits between 0.5 and 1.0 seconds. A
thousand clients arrive spread across half a second instead of stacked in one
instant, so the peak arrival rate is a fraction of what it was. The service
absorbs the first wave, gets warm, and the clients that failed on the first wave
land later still because their second delay is also jittered.

The herd is still a herd. It is no longer a wall.

Two details of this particular multiplier are worth noting.

**It only ever shortens the wait.** The range is `[0.5, 1.0)` of the computed
delay, not `[0.5, 1.5)`. Nobody waits longer than the backoff schedule says, so
adding jitter never makes the worst case slower than the table in section 3.

**It never reaches zero.** The floor of 0.5 means an unlucky client cannot
retry instantly. A multiplier of plain `random.random()` would sometimes produce
a delay of a few milliseconds, which is a client that has effectively ignored the
backoff it just calculated.

The check proves the jitter is really there, and it does so by the only method
that works for randomness, which is to call the function repeatedly and count the
distinct answers.

```python
    spread = {delay_for(3) for _ in range(20)}
    if len(spread) < 2:
        fail("the delay has no jitter, so every client would retry at the same instant")
```

Twenty calls, collected into a set. If somebody deletes the multiplier while
tidying up, the set has one element and the check fails with a message that says
why it mattered rather than saying an assertion was false.

## 5. What must never be retried automatically

Everything so far has been about making failures disappear. This section is the
boundary, and it is the part of the chapter that people get wrong in production
rather than in a tutorial.

Look at what `with_retries` is used on, and more importantly at what it is not
used on. Read the module docstring.

```python
Not everything may be retried. Asking the model again is safe because it
changes nothing outside the conversation. Running a tool that sent an email
is not, which is why nothing in this module wraps a tool call.
```

**Asking the model again is safe.** A model call reads a conversation and
returns text and tool call requests. It touches nothing outside the process. If
you send it twice you get two answers and you use one. The cost is money and
latency, and both are bounded and small.

**Running a tool again is not safe.** A tool exists precisely to change
something outside the process. `write_file` writes to your disk. `run_shell`
starts a subprocess. On a real harness the tool list grows to include things that
send email, open pull requests, call your deployment API and charge cards.

So consider the same timeout in both places. A model call times out after the
server accepted it. You retry, and the worst case is that you paid twice. A tool
call that posts a payment times out after the server accepted it. You retry, and
the worst case is that the customer was charged twice and it is now a support
ticket, a refund, and a conversation about whether your agent should be allowed
near the payment API at all.

The two cases look identical from inside a generic retry helper. That is exactly
why the helper must not be generic.

### Idempotency in plain language

An operation is idempotent when doing it twice leaves the world in the same state
as doing it once.

Reading a file is idempotent. Read it ten times, the file is unchanged and you
have the same content ten times. Setting a value to seven is idempotent. Adding
seven to a value is not, because doing it twice gives you fourteen. Sending an
email is not. Charging a card is not.

The word matters because it converts a vague worry about retries into a property
you can check tool by tool. For each tool, ask whether running it twice is the
same as running it once. If yes, retrying it is safe. If no, retrying it needs
something extra.

### What the something extra is

The mechanism is an idempotency key, and every serious payment and messaging API
implements it, which tells you how universal the problem is.

The caller generates a unique identifier for the operation, before sending it,
and includes it with the request. The receiving service records the key alongside
the result. When a request arrives with a key it has already seen, it does not do
the work again. It returns the result it recorded the first time.

In shape, without a real API.

```python
def charge(amount, idempotency_key):
    if idempotency_key in already_done:
        return already_done[idempotency_key]      # the earlier result, no new charge
    result = payment_api.charge(amount, key=idempotency_key)
    already_done[idempotency_key] = result
    return result
```

Two things about that are load bearing.

**The key is generated by the caller, before the first attempt, and reused on
every retry.** A key generated inside the retry loop would be different each
time, which makes every attempt look like a new operation and defeats the entire
mechanism. The key identifies the intention to charge, not the individual HTTP
request.

**The repeat returns the earlier result rather than an error.** That is what
makes the retry transparent. The caller who lost a response to a timeout asks
again, gets the answer it missed, and never learns whether the second call did
the work or replayed it. Returning an error would be safe but useless, because
the caller still would not know whether the charge went through.

The important consequence is where that logic has to live. The retry helper
cannot supply it, because only the tool knows what its own operation is and what
counts as the same operation. Which is the reason for the design decision this
section exists to explain.

### Why nothing in retry.py wraps a tool call

Say it plainly, because it is a deliberate absence and absences are easy to miss.

`retry.py` contains two functions. `delay_for`, which computes a number, and
`with_retries`, which wraps a callable. Neither of them knows anything about
tools, and `agent.py` does not import `retry` at all. The line that dispatches a
tool is exactly what it was in lesson 04.

```python
                result = tools.run(call["name"], call["arguments"])
```

No retry wrapper. On purpose.

The alternative design is very tempting and it is the trap. You have a nice retry
helper. Tool calls fail sometimes. So you wrap the dispatch line, and now every
tool in the program gets automatic retries for free, including the ones that
should never have got them. The bug this creates does not appear in testing,
because your test tools are all idempotent. It appears the first time somebody
adds a tool with a real side effect, and it appears as a duplicate action with no
error message anywhere, because from the program's point of view nothing went
wrong.

When a tool genuinely needs retrying, the retry belongs inside that tool, next to
the idempotency key that makes it correct. The helper stays where it is, wrapping
the one operation this program has that is genuinely safe to repeat.

### Where with_retries actually goes

There is exactly one correct place for it, and it is inside the provider.
`providers.py` in this folder already puts it there, in a small function that
both providers call.

```python
from retry import with_retries


def open_stream(client, url, payload, headers, attempts=4):
    """Open a streaming request, retrying the failures worth retrying."""

    def once():
        request = client.build_request("POST", url, json=payload, headers=headers)
        response = client.send(request, stream=True)
        if response.status_code >= 400:
            response.read()
            response.close()
            response.raise_for_status()
        return response

    return with_retries(once, attempts=attempts)
```

The provider is the only object in the program that knows it is speaking HTTP.
It is where `httpx` is imported, where `raise_for_status` is called, and
therefore the only place where `httpx.HTTPStatusError` is a meaningful type to
catch. Putting the retry in the loop instead would mean `agent.py` importing
`httpx` in order to know which failures matter, and the loop staying ignorant of
the wire is the property lesson 06 bought and lesson 11 measured.

`check.py` still drives `with_retries` directly against the mock server rather
than through a provider, and that is not duplication. A check holding the helper
by hand can force a `500` twice, count the attempts, and hand in a fake `sleep`
that records the delays instead of waiting them. None of that is reachable
through `stream`, so the check proves the helper behaves and the wiring is
something you read rather than something the check asserts.

Now the complication, and it is the reason the retry lives in `open_stream`
rather than around the whole of `stream`. A retried stream restarts from the
beginning, so any text already printed through `on_text` would print again and
the reader would see half an answer twice. Only the opening of the request is
repeatable, so only the opening is repeated. The comment in `providers.py` says
so at the call site.

```python
            # Only opening the request is retried. Once bytes have arrived the
            # caller has already seen part of an answer, and replaying would
            # splice a second answer onto the first.
```

That is a real design decision with a real cost. A connection that dies halfway
through a long answer is not recovered, and there is no way to recover it without
either buffering the whole response before printing anything, which gives up the
streaming feel lesson 05 built, or making the provider replay only the missing
tail, which no provider gives you the means to ask for.

## 6. Stopping a running agent for real

The other half of the chapter, and the half with the more embarrassing failure
mode.

```python
"""One object that says stop, shared by everything that can be stopped.

An interrupt that only updates the screen is the bug this exists to prevent.
Harnesses people use every day have shipped versions where pressing the
interrupt key printed a cancellation message while the tool it was supposed
to stop kept running to completion.

The same token is checked by the agent loop between turns and by the shell
tool before it starts a process, so one press stops the actual work rather
than only the display.
"""
import threading


class Cancellation:
    def __init__(self):
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise KeyboardInterrupt("cancelled")


NEVER = Cancellation()
```

Thirty one lines, most of which are a docstring.

**What it is.** A single object holding one flag, passed to everything that might
need to stop.

**Why we are doing it.** Because an interrupt that only prints a message is a
lie, and it is a lie that shipped in tools people use daily. The screen says
stopped. The subprocess is still running. The file is still being written. You
believe the agent stopped, so you edit the file it is still editing.

### The press has to reach every layer

When you press Ctrl+C, the agent could be in one of three places, and stopping
means stopping in all three.

**The in flight request.** The model is streaming and text is appearing on your
screen. Stopping means the loop does not start another turn once this one ends.

**A subprocess.** `run_shell` started `pytest` and it is thirty seconds into a
two minute run. Stopping means that process is not left running after the harness
has told you it stopped.

**A pending question.** `ask_in_terminal` printed a permission prompt and is
blocked inside `input`, waiting for you to type `y`. Stopping means the question
goes away and the call it was guarding does not run.

The failure that ships is when one layer hears the interrupt and the others do
not. The display layer is the easiest one to wire up and the one you notice
first, which is exactly why it is the one that gets wired up alone.

### Why one shared token rather than a flag per layer

This is the design question, and it has a specific answer.

The alternative is that each layer owns its own state. The loop has
`self.stopping`. The shell tool has a module level `_cancelled`. The permission
prompt has a third thing. The signal handler sets all of them.

That design works on the day you write it. Here is why it stops working.

**Every new stoppable thing is a new flag, and forgetting one is silent.** Add a
tool that makes a long HTTP request. It needs to be cancellable. If you forget to
add a flag for it and to set that flag in the handler, nothing breaks visibly. It
simply is not cancellable, and you find out during an incident.

**There is no single answer to whether we are stopping.** With one token you can
ask. With four flags there are sixteen states, most of which are nonsense, and
half of the possible bugs are two flags disagreeing.

**The layers are not all on one thread.** `Cancellation` wraps
`threading.Event`, which is the standard library's thread safe one shot flag.
`set` and `is_set` are safe from any thread, so a signal handler, the main loop
and a worker all read the same value with no locking on your part. A plain
boolean would be a data race that works in every test and fails once under load.

A plain boolean would in fact be adequate for the current single threaded code.
`Event` is chosen because the moment a tool runs on a worker thread the boolean
is quietly wrong, and this is a cheap way to never have to think about it.

Notice what the class does not have. No cancel reason, no callback list, no way
to un-cancel. Cancellation is one directional. Once you have said stop, the
answer to whether we are stopping is yes forever, and a token that could be
reset would need rules about who may reset it and when. The command line gets the
same effect by constructing a fresh `Cancellation` for the next turn, which is
one line and has no ambiguity in it.

### Where the loop checks it

Two places in `agent.py`, and both were chosen rather than sprinkled.

```python
    def stop_requested():
        return cancellation is not None and cancellation.cancelled
```

```python
    for _ in range(max_turns):
        if stop_requested():
            raise KeyboardInterrupt("cancelled")
```

```python
        for call in calls:
            if stop_requested():
                raise KeyboardInterrupt("cancelled")
```

Before each turn, and before each tool call. Those are the two moments where the
program is about to start something expensive or something with a side effect.
Checking between the streamed characters of a response would stop a fraction of a
second sooner and would mean threading the token into the provider's parsing
loop, which is a lot of coupling to save half a second.

`cancellation=None` is the default and `stop_requested` handles it, so every
caller written before this lesson still works and simply never stops. The
package version of the same code uses the `NEVER` sentinel at the bottom of
`cancel.py` for the same purpose, which lets it call `raise_if_cancelled`
unconditionally rather than testing for `None` first.

### The pending question, and the subprocess

`ask_in_terminal` already handles the interrupt, and it has since lesson 12.

```python
    try:
        answer = input("Allow? [y]es once, [a]lways for this exact call, [N]o ")
    except (EOFError, KeyboardInterrupt):
        print()
        return DENY
```

A Ctrl+C while a question is pending returns `DENY`, so the call that was waiting
for approval does not run. The loop then reaches the check at the top of the next
call and raises. The question layer and the loop layer arrive at the same outcome
from two different directions, which is what you want when the two layers are
interrupted at slightly different moments.

The subprocess layer is the one to be honest about, and the honest thing is not
what you would guess. `tools.py` in this folder does consult the token, exactly
where the `cancel.py` docstring says it should.

```python
CANCELLATION = None


def run_shell(command):
    ...
    if CANCELLATION is not None and CANCELLATION.cancelled:
        return "Cancelled before the command started."
```

The gap is that nothing in lesson 17 ever assigns `tools.CANCELLATION`. It is
`None` for the whole of this chapter, so the check is dead code here. The first
line in the course that sets it is in lesson 18's `main.py`, where the command
line builds one token and hands the same object to both the loop and the module.
Until that line exists, the token the loop consults and the token the shell tool
consults are not the same object, because the second one is not an object at all.

That is worth seeing rather than being told, because it is the shape of a whole
category of bug. A check written correctly, in the right place, guarding nothing,
because the value it guards on is never supplied. Nothing fails. Nothing warns.
The only symptom is that a feature you can point at in the source does not
happen.

And there is a second gap that survives the wiring. The check runs before the
command starts, so a shell command already running when you press Ctrl+C still
finishes on its own. The `communicate(timeout=SHELL_TIMEOUT)` call in `run_shell` bounds it, and
the loop refuses to start the next one. Killing a command mid run needs a loop
that polls the process while watching the token, which is more
machinery than this chapter wants and is left as an exercise in lesson 18.

### The interrupt handler, and the second press

The token has to be set by something. That something lives in the command line
rather than in the loop, because `agent.py` should not know that keyboards exist.
Here it is from the packaged harness in `src/agentpath/cli.py`, which is what
lesson 18 assembles.

```python
def install_interrupt_handler(agent):
    """Make Ctrl+C stop the work rather than only the display.

    The first press asks the agent to stop, which it notices between turns
    and before running a tool. A second press falls through to the normal
    Python behaviour, so a genuinely wedged process can still be killed.
    """

    def handle(signum, frame):
        if agent.cancellation.cancelled:
            raise KeyboardInterrupt
        print("\nStopping after the current step. Press Ctrl+C again to force it.")
        agent.cancellation.cancel()

    try:
        signal.signal(signal.SIGINT, handle)
    except ValueError:
        pass
```

The first press is cooperative. It sets the flag, tells you what is happening,
and lets the agent stop at the next safe point, which means the session file is
written correctly, the usage total is printed, and the conversation is intact for
`resume`.

**Why the second press falls through to the normal behaviour.** Because
cooperative cancellation depends on the program reaching a check, and a program
that is genuinely wedged will never reach one. A `read` on a socket that a
firewall silently dropped can block for a very long time. A subprocess that is
waiting for input nobody will type will block forever. In both cases the flag is
set, the message has been printed, and nothing is happening.

If the handler swallowed every press, the only remaining option would be another
terminal and `kill`, and a harness whose stop button does not stop is worse than
one that has no stop button, because you sat there pressing it.

So the second press raises `KeyboardInterrupt` from inside the handler, which is
ordinary Python interrupt behaviour. The run dies, the traceback may be ugly, the
session file may be missing its last message. That is the correct trade. The
first press offers a clean stop. The second press guarantees a stop.

The message earns its place too. Without it, the first press appears to do
nothing, because the agent is still finishing a turn, and a user who thinks the
button is broken presses it four more times.

`except ValueError` covers `signal.signal` refusing to install a handler when
called from a thread that is not the main one, which happens when the harness is
embedded in something bigger. Failing to install a nice to have handler should
not prevent the program from starting.

## 7. When the model gets stuck

The third failure from section 1, and the only one where nothing raises.

`max_turns=10` is the only bound the loop has ever had. It counts turns
faithfully and it notices nothing. Ten turns of steady progress and ten turns of
the same failing call look exactly alike to a counter, and both end with the same
`RuntimeError`.

Watch how a model spends a budget on nothing. It calls `grep_files` for
`def handle_payment` and gets no matches, because the function is called
`process_payment`. A person would widen the search. A model under pressure to
produce a tool call frequently does this instead.

```text
[calling grep_files with {'pattern': 'def handle_payment', 'glob': '*.py'}]
[grep_files returned no matches]

[calling grep_files with {'pattern': 'def handle_payment', 'glob': '*.py'}]
[grep_files returned no matches]

[calling grep_files with {'pattern': 'def handle_payment', 'glob': '*.py'}]
[grep_files returned no matches]
```

Identical arguments, identical results, and each turn resends the entire growing
conversation, so the loop that produces nothing is also the most expensive part
of the run. This happens more with small local models, and it happens with large
ones too when a tool keeps returning an error the model does not understand.

### The fingerprint

```python
REPEAT_LIMIT = 3
```

```python
    recent = []
    warned = set()
```

```python
            current = loose_signature(call["name"], call["arguments"])
            recent.append(current)
            going_in_circles = recent[-REPEAT_LIMIT:].count(current) >= REPEAT_LIMIT
```

`loose_signature` sits beside the `signature` lesson 12 wrote for remembering
permission decisions, and it is the forgiving cousin. It strips the whitespace
off each value before hashing.

```python
def loose_signature(name, arguments):
    """The same idea as signature, but forgiving about the edges of a value.

    This one is for spotting a model going in circles, not for deciding
    what is allowed. A model that retries with a trailing space added has
    changed nothing and should not get a fresh fingerprint for it. A model
    that changes a letter's case has, because a case sensitive search for
    Error and a search for error are different searches. Permission
    decisions keep using the exact signature, because there the difference
    between two nearly identical commands can be the whole point.
    """
    # Trailing and leading space only. Folding case as well made three
    # genuinely different searches look identical, and a model widening a
    # pattern from Error to error was told it was going in circles.
    flattened = {key: str(value).strip() for key, value in arguments.items()}
    return f"{name}({json.dumps(flattened, sort_keys=True)})"
```

**What it is.** A string that identifies one exact call.

```text
grep_files({"glob": "*.py", "pattern": "def handle_payment"})
```

**Why the arguments are included.** Because the tool name alone is far too
coarse. An agent working through a codebase might call `read_file` fifteen times
in a row, and that is not being stuck, that is doing the job. Repeating
`read_file` on the same path fifteen times is being stuck. The difference is
entirely in the arguments.

**Why `sort_keys=True`.** Because `{"a": 1, "b": 2}` and `{"b": 2, "a": 1}` are
the same call, and streamed JSON does not guarantee key order. Without sorting,
a model that emitted its keys in a different order on the second attempt would
produce a different fingerprint and slip past the detector, and it would do so
intermittently, which is the worst kind of bug to chase.

**Why `recent[-REPEAT_LIMIT:]` rather than counting the whole list.** Because it
must be three times in a row, not three times ever. Only the last three
fingerprints are examined, so a call that appears at turn one, turn five and turn
nine, with real work in between, is not a loop. A model that reads a file,
changes it, runs the tests, and reads the same file again is behaving correctly,
and a detector that punished that would be worse than no detector.

The two jobs deliberately use two functions. Permissions keep the exact
`signature`, because there the difference between two nearly identical
commands can be the whole point. The loop uses the forgiving one, because a
model that retries with a trailing space added has changed nothing and should
not get a fresh fingerprint for it. Case is kept, since a search for `Error`
and a search for `error` are different searches, and an earlier version that
folded case told a model widening its pattern that it was going in circles.

### The warning

```python
            elif going_in_circles:
                # A turn limit counts but does not notice that nothing is
                # changing. Saying so plainly gives the model a chance to
                # change course instead of spending the whole budget.
                result = (
                    f"Error: {call['name']} has been called with these exact arguments "
                    f"{REPEAT_LIMIT} times in a row and nothing has changed. You are going "
                    "in circles. Stop repeating it and try a different approach."
                )
                print(f"\n[{call['name']} is going in circles]")
```

The tool is not run. Its result is replaced with a sentence describing the
situation, and that sentence goes into the conversation as an ordinary tool
result.

**Why it warns before stopping.** Because the model may simply not have realised.

That sounds generous and it is actually mechanical. A model sees its own previous
tool calls in the conversation, but noticing that three of them were byte for
byte identical is a comparison task performed on text that is scattered through
a long context, in between file contents and its own reasoning. Models are
routinely bad at it, and the failure is not stubbornness. Nobody told it.

Telling it works surprisingly often. The message names the tool, states the
count, says plainly that nothing has changed, and asks for a different approach.
Given that, a model will usually widen the pattern, try a different tool, or say
that it cannot find the thing and ask you. All three of those are better outcomes
than a `RuntimeError` at turn ten, and the warning costs one turn.

Note where the warning sits in the `if` chain. After `call["error"]`, before the
permission check. A malformed call is a different problem with its own message,
and there is no reason to ask a person to approve a call we have already decided
not to run.

### And the stop

```python
            if going_in_circles and current in warned:
                giving_up = {
                    "role": "assistant",
                    "content": (
                        f"Stopping. {call['name']} was warned about repeating itself and "
                        "repeated anyway. Continuing would only cost money."
                    ),
                }
                remember(giving_up)
                print(f"\n{giving_up['content']}")
                return giving_up["content"], messages
            if going_in_circles:
                warned.add(current)
```

Read the order carefully, because it is what makes the two stage behaviour work.

The first time a fingerprint is detected as circling, it is not in `warned`, so
the first branch is skipped and the last two lines add it. The model gets the
warning in its next request.

If the same fingerprint comes back again, it is now in `warned`, and the run
ends. Not with an exception. With a normal return of a message and the full
conversation, so the session file is complete, the usage total prints, and you
can read exactly what happened and resume from it if you want to.

**Why stop at all rather than warn forever.** Because the warning has already
been given and ignored, and the evidence at that point is that the model is not
going to recover on its own. Every further turn resends a conversation that has
grown by another tool call, so continuing costs more per turn than the turn
before it, and produces the same nothing.

**Why `warned` is a set of fingerprints rather than a single boolean.** Because
an agent can get stuck twice on two different things in one run, and being warned
about `grep_files` should not consume the one warning available for
`read_file`. Keying the warning to the fingerprint gives each distinct loop its
own chance to recover.

The tool result is still appended before the giving up message, which keeps the
conversation valid. Every tool call in it has a matching result, so the session
file can be replayed or resumed without hitting the pairing trap from lesson 14.

## 8. How the failures in check.py are produced

Everything in this chapter is about behaviour under failure, and you cannot test
behaviour under failure without failures. There are two ways to get them and only
one of them is a test.

The way that is not a test is pointing at a real provider and waiting. You cannot
ask a real endpoint for a `429` at a particular moment. You would have to hammer
it until it rate limited you, which is rude, slow, dependent on an API key,
dependent on the network, and produces a suite that passes on your machine and
fails in CI for reasons nobody can reproduce. A test that fails at random is not
a test, it is a source of noise that teaches the team to rerun the build.

The way that is a test is a server that fails exactly when you tell it to. That
is what the mock server from lesson 06 grew a feature for.

```python
    def _maybe_fail(self):
        """Return True when this request should fail, per the caller's headers.

        The caller drives this rather than the server failing on its own,
        because a test that fails at random is not a test.

        The counter lives on the server rather than in a module global so
        that each server starts fresh. A shared global would make one test
        depend on how many tests ran before it, which is the kind of bug
        that only appears when the whole suite runs.
        """
        status = self.headers.get("X-Mock-Fail")
        if not status:
            return False
        times = self.headers.get("X-Mock-Fail-Times")
        if times is not None:
            counts = getattr(self.server, "fail_counts", None)
            if counts is None:
                counts = self.server.fail_counts = {}
            key = f"{status}:{times}:{self.path}"
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > int(times):
                return False
        code = int(status)
        headers = {"Retry-After": "2"} if code == 429 else {}
        self._send_json(
            {"error": {"type": "mock_failure", "code": code}},
            status=code,
            extra_headers=headers,
        )
        return True
```

Two headers, and between them they express every scenario this chapter needs.

**`X-Mock-Fail`** names the status code to return. Send `X-Mock-Fail: 500` and
this request comes back `500`. No header means a normal response, so every check
written before this lesson is unaffected.

**`X-Mock-Fail-Times`** says how many times. It is what turns a permanent failure
into a temporary one, which is the interesting case, because permanent failure
only proves you gave up and temporary failure proves you recovered. With
`X-Mock-Fail-Times: 2`, the counter increments on each request, the first two
requests fail, and from the third the `counts[key] > int(times)` test sends the
request through to the real handler.

**The `Retry-After` header on a `429`.** One line, and it is the entire reason
section 3 is testable.

```python
        headers = {"Retry-After": "2"} if code == 429 else {}
```

The mock behaves the way a real provider behaves, which is to attach the header
to the status that means slow down and to no other status. So a check can demand
a `429`, know for certain that a `Retry-After: 2` is coming back, and assert that
the client waited exactly two seconds rather than the one to two seconds its own
formula would have produced. Without the mock sending that header there would be
no way to distinguish obeying the server from a lucky roll of the jitter.

### Why the counter lives on the server object

The docstring makes this point and it is worth expanding, because it is the kind
of thing you get wrong once and remember forever.

```python
            counts = getattr(self.server, "fail_counts", None)
            if counts is None:
                counts = self.server.fail_counts = {}
```

The obvious implementation is a module level dictionary. It works when you run
one check. Then CI runs thirty six checks in a row against one process, and
the counter has already been incremented by an earlier lesson, so the failure
budget is used up and your two failures become one. The check fails, and it fails
only in CI, only when the full suite runs, and only in whatever order the
directory listing happened to produce.

Attaching the state to the server instance means each `serve()` starts with
nothing. The key includes the status, the count and the path, so two different
scenarios in the same check cannot bleed into each other either.

### What the checks look like from the client side

```python
def post(headers=None):
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    response = httpx.post(
        f"{base_url}/chat/completions",
        json={"model": os.environ["AGENTPATH_MODEL"], "messages": [{"role": "user", "content": "hi"}]},
        headers=headers or {},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()
```

One helper, and the failure is requested per call by passing headers. Three
scenarios follow from it.

```python
    def flaky():
        attempts.append(1)
        return post({"X-Mock-Fail": "500", "X-Mock-Fail-Times": "2"})

    body = with_retries(flaky, sleep=lambda seconds: None)
```

Fail twice, then work. The assertion is that `attempts` has exactly three
entries, which is two failures and one success. Two would mean it gave up early.
Four would mean it retried after succeeding.

```python
    def broken():
        bad_attempts.append(1)
        return post({"X-Mock-Fail": "400"})
```

Fail permanently with a client error. The assertion is that `bad_attempts` has
exactly one entry and that the `httpx.HTTPStatusError` escaped. This is the
section 2 rule expressed as a count, and it would fail loudly if somebody added
`400` to `RETRYABLE_STATUS` for a quiet life.

```python
    waited = []
    try:
        with_retries(lambda: post({"X-Mock-Fail": "429"}), attempts=2, sleep=waited.append)
    except httpx.HTTPStatusError:
        pass
    if waited != [2.0]:
        fail(f"the Retry-After header of 2 seconds was not obeyed. Waited {waited}")
```

This one is worth admiring. `sleep=waited.append` is the whole trick. The
`sleep` parameter exists so that a caller can supply something other than
`time.sleep`, and here the substitute records the number instead of waiting for
it. So the check runs instantly and still asserts on the exact delay that a real
run would have waited.

`attempts=2` means exactly one gap between attempts, so `waited` must be a list
of one number. And that number must be `2.0` on the nose. The jitter formula for
attempt one produces something in `[0.5, 1.0)`, so a client that ignored the
header could not produce `2.0` by accident. The equality is the proof that the
header won.

## 9. Running check.py

From inside the lesson folder, with an endpoint configured.

```bash
cd lessons/17-errors-and-retries
python check.py
```

Or run every lesson at once against the built in mock server, which is what
continuous integration does.

```bash
python ci/run_lessons.py
```

A passing run looks like this.

```text
OK a server error was retried until it worked, after 3 attempts
OK a bad request is not retried, because the same wrong request stays wrong
OK when the server says when to come back, we wait exactly that long
OK the delay is jittered across 20 different values
OK a cancelled token stops work rather than only printing a message

[calling read_file with {'path': 'nowhere.txt'}]
[read_file returned Error: nowhere.txt does not exist]

[calling read_file with {'path': 'nowhere.txt'}]
[read_file returned Error: nowhere.txt does not exist]

[read_file is going in circles]

[read_file is going in circles]

Stopping. read_file was warned about repeating itself and repeated anyway. Continuing would only cost money.
OK a model repeating one call is warned, then stopped, without burning every turn
```

Six `OK` lines, and each one is a claim from a different section of this
chapter. The trace in the middle belongs to the sixth, which is the only one
that runs the loop.

The first is section 2's good half. A `500` came back twice and the third attempt
returned a real body with real choices in it.

The second is section 2's bad half. The `400` escaped on the first attempt, and
the count proves no time was wasted on it.

The third is section 3. The recorded delay is exactly `2.0`, which is the
server's header rather than our formula.

The fourth is section 4. Twenty calls to `delay_for(3)` produced twenty distinct
floats, so the multiplier is doing its job. If you see a small number here rather
than twenty, that is fine, since identical floats are possible in principle, but
a `1` means the jitter is gone.

The fifth is section 6, and it is the smallest possible version of the claim.
Cancel a token, call `raise_if_cancelled`, and a `KeyboardInterrupt` must come
out. The check asserts on the exception rather than on a printed message, which
is the same discipline lesson 11 argued for at length. An interrupt that prints
is the bug. Only the raised exception proves anything.

The sixth is section 7. A fake provider returns the same `read_file` call
forever, and the run has to end because the repeat detector noticed, not because
`max_turns` ran out. `max_turns` is twenty here on purpose. A stuck model that is
stopped by the turn limit proves nothing about the detector, so the check gives
the limit enough room that reaching it would be the failure.

Notice what the first five do not do. They never start a real agent run, never
call a tool, and never wait a real second. Every one of those scenarios is driven
through `with_retries` and `Cancellation` directly, which is why the check
finishes instantly and gives the same answer every time. Only the sixth needs a
loop, and it gets a fake provider rather than a network.

If the first line fails, look at whether the mock server is being reached at all,
since a connection error would be counted as a transport failure and retried four
times before surfacing. If the third fails and the recorded wait is a number
between one and two, `delay_for` is computing the formula before checking the
header, which means the two blocks have been swapped. If the fourth fails, the
jitter multiplier has been deleted.

## 10. What you cannot do yet

You have a harness. What you do not have is a program.

Count what part 3 has built. Permissions with three answers and a memory.
Sessions as JSONL you can read in a text editor. Context that fits a budget
without breaking tool call pairs. Usage counting and prompt caching. Retrieval
you can measure rather than argue about. Retries, backoff, jitter, cancellation
and circuit detection.

Now count the folders those live in.

```text
lessons/11-mini-coding-agent/    agent.py providers.py prompt.py tools.py
lessons/12-permissions/          + permissions.py
lessons/13-sessions/             + session.py
lessons/14-context-management/   + context.py
lessons/15-token-economy/        + usage.py
lessons/16-retrieval/            + retrieval.py
lessons/17-errors-and-retries/   + retry.py cancel.py
```

Seven folders, and every one of them contains a full copy of everything that came
before. `prompt.py` is identical in every folder from lesson 10 onwards.
`permissions.py` is identical in every folder from lesson 12 onwards.
`retrieval.py` appears in this folder byte for byte as it appeared in lesson 16.
There are thirteen Python files here and two of them are new.

That was the right choice for teaching. Every lesson stands alone, you can run
any chapter without having read the previous one, and a diff between two folders
shows exactly what a chapter changed. It is a terrible choice for a program. Fix
a bug in `tools.py` and there are seven copies to fix.

The duplication is only the visible half of the problem. The real gap is that
nothing here is assembled. `retry.py` reaches the provider, and that is as far as
the wiring goes. `cancel.py` exists and no signal handler sets it, so nothing
ever calls `cancel`. `tools.CANCELLATION` exists and nothing ever assigns it, so
the shell tool's check reads `None` forever. There is no way to resume a session
from the command line, no way to run one task and exit, no `--yes` for scripts,
no place where the budget from lesson 14 and the permissions from lesson 12 and
the cancellation from this chapter all meet in the same object.

**Lesson 18, the harness.** One new file, `main.py`, where every one of those
parts finally meets. A command line built with `argparse`, taking the task as a
positional argument and `--workspace`, `--session`, `--resume`, `--budget` and
`--yes` as flags. A session name chosen three different ways, and `--resume`
winning by supplying a name rather than by copying a file. A signal handler that
sets the cancellation token, and the line right beside it that hands the same
token to `tools.py`, which is what stops the shell tool's check from being dead
code. Then a milestone check that runs the assembled program end to end.

Be clear about what lesson 18 does not do, because two things stay as they are.
`run` is still the printing function it has been since lesson 04, so the terminal
drawing is still inside the loop. And the parts are still handed to it as keyword
arguments rather than held by an object. The installed package under
`src/agentpath/` does go further, with an `Agent` class, a loop that yields typed
events, and a command line with `chat`, `run` and `resume` as subcommands, and
lesson 18 points at it wherever the two differ. The lesson folder stays a flat
script on purpose, because the point of the chapter is that you can read the
whole assembly in one file.

Nothing in lesson 18 is a new idea. It is the second milestone, and like the
first one its job is to show that the parts fit, to look back at the seams, and
to be honest about what is still missing.

Before you go on, do two things. Run `python ci/run_lessons.py` from the
repository root and watch every check pass. Then open `retry.py` and
`cancel.py` side by side and notice that between them they are ninety eight
lines, most of it docstring, and that they answer three of the five ways your
agent breaks in the first hour of real use.

On to lesson 18.
