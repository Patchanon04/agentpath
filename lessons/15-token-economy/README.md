[อ่านภาษาไทย](README.th.md)

# Lesson 15. Token economy

Every chapter so far has added a capability. This one adds a number.

That sounds like a smaller thing and it is not. Lesson 14 built machinery whose
entire job is to manage a resource, and that machinery has never once been
allowed to see the resource. `budget` is a number you picked. `estimate_tokens`
is a division by four. Neither of them has ever been compared against anything
real, because nothing real has ever entered the program.

This chapter puts the real number in. Then it spends the rest of its length on
what you do once you have it, which is mostly one idea about ordering that is
worth more than every other optimisation in this file combined.

Files in this folder.

```text
lessons/15-token-economy/
  usage.py       new. Usage.add, Usage.cost, Usage.summary. forty nine lines
  providers.py   lesson 06's two providers, now returning what the request cost
  agent.py       lesson 14's loop, plus a usage parameter and a circuit breaker
  check.py       five checks, two of which are the facts the chapter rests on
  context.py     unchanged from lesson 14
  permissions.py unchanged from lesson 12
  session.py     unchanged from lesson 13
  prompt.py      unchanged from lesson 10
  tools.py       unchanged from lesson 09
  README.md      this file
```

One new file of forty nine lines. Both providers gain three lines each. The loop
gains two lines for usage and a repeat detector that section 6 explains.

---

## 1. The problem lesson 14 left you with

You finished lesson 14 with `fit_to_budget`. It groups the conversation into
exchanges, keeps the newest ones that fit, and never strands a tool result away
from its tool call. It is correct, it is deterministic, and it is eighty lines
you can read in a sitting.

It is also completely blind.

Look at what actually decides when it fires. `estimate_tokens` counts characters
and divides by four, then adds four per message for overhead. That is the whole
model. `budget` is whatever integer the caller passed in, and the caller got that
integer by looking at a model card and guessing something smaller. Nowhere in
fourteen lessons has the program compared either number to what a provider
actually charged for a request.

So there are two failures available to you and no way to tell them apart. You
might be trimming at sixty percent of the real window, throwing away context the
agent needed for no reason. Or you might be trimming at ninety five percent and
still getting rejected, because the estimate ran low on exactly the content your
task produces. Both feel identical from the outside. Both look like the agent
being stupid.

And beneath that sits the larger gap. Nothing in this program has ever printed a
cost. You cannot say whether the task you just ran was a tenth of a cent or forty
cents, and you certainly cannot say which part of it was the expensive part.
Without that number every optimisation you attempt is superstition. You will
shorten the system prompt, which is 612 characters, and feel that you have
achieved something, while a `grep_files` result of a hundred and eighty lines
rides along in every request for the rest of the session and costs you thirty
times more.

### The growth, measured

Here is the first thing `check.py` prints. This is not a diagram. It is what the
provider reported on four consecutive requests.

```text
OK the same conversation cost more every turn, [2, 12, 22, 32]
```

Four numbers, each one the `prompt_tokens` the provider charged for one request.
Two, then twelve, then twenty two, then thirty two.

The conversation those four requests came from is the one in `check.py`, and it
is deliberately about as boring as a conversation can be.

```python
    conversation = [{"role": "user", "content": "Say hello."}]

    for turn in range(4):
        body = send(conversation)
        usage.add(body["usage"])
        prompts.append(body["usage"]["prompt_tokens"])
        conversation.append({"role": "assistant", "content": body["choices"][0]["message"]["content"] or ""})
        conversation.append({"role": "user", "content": f"And again, turn {turn}."})
```

Nobody reads a file. Nobody calls a tool. Nobody says anything longer than a
sentence. The user says "Say hello.", then says "And again, turn 0.", and so on.
Each turn adds about eighteen characters of new material.

And the cost of a request went from 2 to 32, which is sixteen times.

That is the shape of the problem, and it is the subject of the next section.

---

## 2. Why the same conversation costs more every turn

**What this is.** A language model is stateless. It has no memory of your
previous request. Lesson 02 established this and it has been quietly setting the
economics of everything since. The only reason turn four knows what happened on
turn one is that your program sent turn one again, in full, inside the turn four
request.

**Why it matters here.** It means the price of turn N is not the price of turn
N's new material. It is the price of turns one through N minus one, plus the new
material, every single time. You are not paying for a conversation. You are
paying for the sum of every prefix of a conversation.

Walk the four numbers from section 1 and watch it happen. The mock server counts
about four characters to a token, so the arithmetic is checkable by hand.

| Turn | What the request contains | Prompt tokens |
| --- | --- | --- |
| 1 | `Say hello.` | 2 |
| 2 | all of turn 1, plus the reply, plus `And again, turn 0.` | 12 |
| 3 | all of turn 2, plus the reply, plus `And again, turn 1.` | 22 |
| 4 | all of turn 3, plus the reply, plus `And again, turn 2.` | 32 |

Now add the column up. The provider charged for 68 prompt tokens across the run.
The largest single request was 32 tokens, and the total unique material in the
conversation at the end was those same 32 tokens. So you paid for 68 to send 32.
Twice over, on a four turn conversation where nothing interesting happened.

`check.py` prints that total on its second line.

```text
OK usage adds up across calls, 4 calls, 68 prompt tokens, 24 completion tokens
```

**Why this grows the way it does.** Each turn adds a roughly constant amount of
new text, and each turn resends everything before it, so the cost of turn N is
proportional to N and the total across the run is proportional to N squared. It
is quadratic in the number of turns, not linear. That distinction is the whole
reason this is a chapter rather than a footnote, because a linear cost that
surprises you is twice what you expected and a quadratic one is thirty times.

Here is what that looks like at a realistic size. Take a ten turn coding task
with a system prompt and seven tool schemas as a fixed prefix of about 1400
tokens, and a file read or a grep result of about a thousand tokens arriving on
each turn. This is the arithmetic, run rather than asserted.

```python
from usage import Usage

usage = Usage()
for turn in range(10):
    usage.add({"prompt_tokens": 1400 + 1000 * turn, "completion_tokens": 400})

print(usage.summary())
print("last request alone:", usage.per_call[-1]["prompt_tokens"])
```

```text
10 calls, 59000 prompt tokens, 4000 completion tokens
last request alone: 10400
```

Fifty nine thousand prompt tokens billed. The largest single request was ten
thousand four hundred. The unique material was ten thousand four hundred. You
paid roughly five and a half times over for it, and the ratio gets worse with
every turn you add.

**Why we are not just going to make the conversation shorter.** That was lesson
14 and it is necessary, but it attacks the wrong term. Trimming reduces the size
of each request. The multiplier that turns each request into a bill is the number
of times a given block of text is resent, and trimming does nothing about that
until the block falls out of the window entirely. Section 5 attacks the
multiplier directly, which is why it is the longest section in this file.

---

## 3. Where the real numbers come from

**What this is.** Every provider tells you, in the response, what that request
actually cost. Not an estimate. The number their own billing uses, produced by
their own tokeniser on the exact bytes you sent.

**Why we use it.** It is the only number in the system that is not a guess. Every
other count in this program, including the one lesson 14 makes decisions with,
is your program's opinion about somebody else's tokeniser. The reported usage is
the tokeniser's own answer.

**Why not compute it ourselves.** Section 4 is entirely about that question and
the answer is worse than you expect.

### Pulling it out of an OpenAI style stream

The usage arrives as one more chunk in the same stream that carries the text.
Here is the part of `OpenAICompatProvider.stream` that catches it.

```python
                    chunk = json.loads(data)
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                    if not chunk.get("choices"):
                        continue
                    delta = chunk["choices"][0].get("delta", {})
```

Compare that with the same four lines in lesson 14, which were one line.

```python
                    delta = json.loads(data)["choices"][0].get("delta", {})
```

Three changes, and two of them are load bearing.

**The chunk is parsed into a variable now.** Lesson 14 parsed and subscripted in
one expression, which is fine when every chunk has the same shape.

**`if chunk.get("usage")` runs before anything touches `choices`.** Usage arrives
last, after the content is finished, and the value is `null` on every chunk
before that one. The `.get` with a truthiness test handles both the missing key
and the null in one condition, and because the variable is initialised to `{}` at
the top of the method, a provider that never sends usage at all leaves an empty
dictionary rather than raising.

**`if not chunk.get("choices"): continue` is the line that would have crashed.**
On a real OpenAI compatible endpoint the final usage chunk carries an empty
`choices` list. Lesson 14's one liner would have done `[][0]` on it and died with
an `IndexError` in the middle of a working stream. The guard is not defensive
programming for its own sake, it is the specific shape of the specific chunk we
just started reading.

There is a detail here that will bite you against the real OpenAI API and not
against the mock. OpenAI does not send the usage chunk in a stream unless you ask
for it, with `"stream_options": {"include_usage": true}` in the payload. The
payload in `providers.py` does not send that, because many OpenAI compatible
gateways emit usage unprompted and adding a field they do not recognise is a
worse default for a course. If your counts come back as zeros against a real
endpoint, that is the first thing to add.

### Pulling it out of an Anthropic style stream

The Anthropic branch is two lines and the same idea.

```python
                    event = json.loads(data)
                    if event.get("usage"):
                        usage = event["usage"]
```

There is no `choices` array to trip over here, because the Anthropic stream is a
sequence of typed events rather than a sequence of deltas, and the loop below
already dispatches on `event.get("type")`.

Now the honest part, because this is a course and the code in this folder has a
real gap in it. The native Anthropic API does not use the field names
`prompt_tokens` and `completion_tokens`. It reports `input_tokens` and
`output_tokens`, along with `cache_creation_input_tokens` and
`cache_read_input_tokens` when caching is in play, and it splits them across two
events rather than sending one at the end. `Usage.add` reads `prompt_tokens` and
`completion_tokens` with a default of zero, so against a real Anthropic endpoint
it would count the calls correctly and the tokens as zero, silently.

The mock server sends OpenAI style field names on both endpoints, so `check.py`
passes. That is a real limitation and you should know it is there.

**Where the fix belongs, and why.** In the provider, not in `Usage`. The provider
is already the one place in this program that knows the two dialects apart. It
translates the message format in `_to_wire`, it translates the tool schemas from
`parameters` to `input_schema`, and translating the usage field names is exactly
the same job. Putting an `if "input_tokens" in reported` branch inside `Usage`
would make the accounting layer know which vendors exist, which is precisely the
knowledge lesson 06 spent a chapter pushing behind the `stream` interface. Three
lines in `AnthropicProvider.stream`, normalising the dictionary before returning
it, and everything above stays vendor neutral.

### How Usage adds it up

```python
    def add(self, reported: dict) -> None:
        """Record what one request actually cost, as the provider reported it."""
        if not reported:
            return
        self.calls += 1
        self.prompt_tokens += reported.get("prompt_tokens", 0)
        self.completion_tokens += reported.get("completion_tokens", 0)
        self.per_call.append(reported)
```

Six lines, and three of them are decisions.

**`if not reported: return` means a request that reported nothing does not count
as a call.** This is arguable and it is worth saying which way it is arguable. It
keeps `calls` honest as a count of requests you have real numbers for, so
`summary()` never implies you measured something you did not. The cost is that a
provider which silently stops reporting usage looks like a provider that stopped
being called, and you would go looking in the wrong place. If you would rather
know, increment `calls` before the guard and add a `unreported` counter.

**`.get(name, 0)` rather than `reported[name]`.** Providers add fields and
occasionally omit them, and an accounting layer that raises a `KeyError` in the
middle of a working agent run has traded a wrong number for a dead process. A
missing field costs you accuracy in one column. A crash costs you the run.

**`per_call.append(reported)` keeps the whole dictionary, not the two numbers we
understood.** This is the most useful line in the file and it is easy to skip.
The reported usage frequently contains fields `cost` knows nothing about, such as
`cache_read_input_tokens`, `cache_creation_input_tokens`, and on some providers a
separate count for reasoning tokens. Summing only what you currently understand
throws the rest away at the exact moment it arrives. Keeping the raw dictionaries
means that when you want to know your cache hit rate in section 5, the data is
already sitting in `usage.per_call` from runs you did last week.

The rest of the class is arithmetic.

```python
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
```

And the loop consults it in two lines, in the same style as everything else part
three added.

```python
        text, calls, reported = provider.stream(
            to_send(), schemas, on_text=lambda piece: print(piece, end="", flush=True)
        )
        if usage is not None:
            usage.add(reported)
```

`usage` is a parameter with a default of `None`, so a caller who does not care
about cost passes nothing and the loop does nothing. The loop counts no tokens
itself, knows no prices, and has no opinion about what a call should cost. It
consults an object, exactly as it consults `permissions` and `budget`. That is
the fifth time this pattern has appeared and it is why `run` has not needed to
change shape to gain any of the five.

---

## 4. Why a local tokeniser is the wrong tool for deciding

**What a tokeniser is.** A model does not read characters. It reads tokens, which
are chunks of bytes chosen by a compression algorithm that was fitted to a
training corpus. The mapping from text to tokens is a table, and the table is
part of the model, not part of the language.

**Why this matters more than it sounds like it should.** Different companies fit
different tables. The same sentence is not the same number of tokens to two
different vendors, and it is not off by a rounding error. It is off by enough to
change your decisions.

Here is the measurement, on real content from this folder, using three OpenAI
encodings that `tiktoken` will hand you and the character estimate from lesson
14.

```python
import json
import os

os.environ["AGENTPATH_WORKSPACE"] = "."
import tiktoken
import prompt
import tools

encodings = {name: tiktoken.get_encoding(name) for name in ("p50k_base", "cl100k_base", "o200k_base")}
samples = {
    "system prompt": prompt.build_system_prompt(os.getcwd()),
    "tool schemas": json.dumps(tools.SCHEMAS),
    "read_file of tools.py": tools.run("read_file", {"path": "tools.py"}),
    "a grep result": tools.run("grep_files", {"pattern": "def ", "glob": "*.py"}),
}
for name, text in samples.items():
    counts = {k: len(e.encode(text)) for k, e in encodings.items()}
    print(name, len(text), len(text) // 4, counts)
```

| Sample | Characters | `// 4` estimate | p50k | cl100k | o200k |
| --- | --- | --- | --- | --- | --- |
| system prompt | 612 | 153 | 149 | 133 | 134 |
| tool schemas | 2595 | 648 | 669 | 649 | 649 |
| `read_file` of `tools.py` | 4035 | 1008 | 1155 | 929 | 931 |
| a `grep_files` result | 1998 | 499 | 742 | 541 | 541 |

Read the last row carefully. The same 1998 bytes are 742 tokens to one counter
and 541 to another. That is a 37 percent difference, and both of those tokenisers
came from the same company. The lesson 14 estimate calls it 499, which is 8
percent under the middle answer and 33 percent under the high one.

Two conclusions follow and they are different from each other.

**A tokeniser built for one company does not count another company's tokens.**
There is no shared standard here and no reason there would be. If three
generations of one vendor's own encodings disagree by 37 percent on a grep
result, the idea that any of them tells you what a different vendor will charge
is not slightly optimistic, it is unfounded. And for several vendors you cannot
even install the tokeniser to be wrong with, because it is not published.

**The error is largest on exactly the content agents produce.** Notice which row
is worst. The prose system prompt is within a few percent across all four
counters, because ordinary English is what these tables were fitted on. The
mangled, punctuation dense, path and colon and line number shaped output of a
grep is where they diverge, and grep output is most of what an agent's
conversation is made of. The estimate is most wrong precisely where you have the
most of it.

**Why this is fatal for a harness rather than merely annoying.** `providers.py`
in this folder talks to two different services behind one interface. That was the
whole point of lesson 06 and it remains right. But `fit_to_budget` sits above
that interface with one counter, and the same conversation gets the same estimate
regardless of which service it is about to be sent to. A single counter serving
two vendors is guaranteed to be wrong for at least one of them, and you have no
way to know which. You are making a trimming decision, which throws away work the
agent did, on a number that was computed for somebody else.

**So what is the estimate for.** It is a trigger, not a measurement, and lesson
14's docstring already says so in as many words.

```python
def estimate_tokens(messages):
    """A rough count, deliberately not exact.

    Every provider counts differently and none of them count the way a
    character estimate does. Use this to decide when to start trimming, then
    use the number the provider reports afterwards to know what actually
    happened. Trusting a local estimate to be exact is how people end up
    trimming to ninety percent of a window and still getting rejected.
    """
```

That is the division to hold on to, and it is the point of this whole section.

The local estimate answers "should I look at this". It runs for free, it runs
before the request rather than after, it needs no network, and being 30 percent
wrong in a known direction is fine for a question whose answer is a yes or a no.
Set your budget with the error in mind, which in practice means trimming earlier
than the model card suggests.

The reported number answers "what happened". It is exact, it is the only thing
that will ever reconcile with an invoice, and it arrives too late to prevent
anything. You use it to check whether your budget was in the right place, to
watch your cache hit rate, and to find out which part of a run was expensive.

Using either one for the other's job is the mistake. Deciding with the reported
number is impossible because it does not exist yet. Reporting with the estimate
is how you end up confidently telling somebody a number that has never been true.

---

## 5. Prompt caching, and the one rule that follows from it

This is the section that pays for the chapter. Everything in section 6 put
together will not save you what this section saves you, and unlike everything in
section 6 it costs you no capability at all.

### What caching means here

When a provider handles your request, most of the work is processing the input
before a single token of output exists. That work depends only on the input, and
if the beginning of your input is byte for byte identical to the beginning of an
input it handled a few minutes ago, it can reuse what it already computed instead
of computing it again.

That reuse is what prompt caching is, and providers charge very differently for
it. Reading a cached prefix typically costs something in the region of a tenth of
what processing the same tokens fresh would cost. Writing a prefix into the cache
in the first place usually costs slightly more than processing it normally, in
the region of a quarter more. The exact ratios are per vendor and per model and
they change, so check the price page for the model you are actually on rather
than trusting any number in a tutorial, this one included.

Note what is being reused. It is the provider's internal work on the prefix, not
your text. There is nothing you can cache on your own machine that achieves this,
which is why this is a section about how to arrange a request rather than a
section about writing a cache.

### Why an agent is the ideal case for it

Go back to section 2. The thing that made your bill quadratic was that every
request resends the entire conversation so far. Now read that sentence again with
caching in mind. Every request resends a prefix the provider has already seen,
because turn N's request is turn N minus one's request plus a bit on the end.

The property that makes an agent expensive is the exact property that makes it
cacheable. The 59,000 prompt tokens from section 2 contain about 10,400 unique
tokens and roughly 48,600 tokens of prefix that was already sent on an earlier
request. At a tenth the price, those 48,600 become the equivalent of about 4,900.
The prompt side of that run drops from 59,000 to around 15,300 chargeable, which
is about a quarter, and you changed nothing about what the agent does.

That is the prize. Now the condition attached to it.

### The rule

**Anything that never changes goes at the front. Anything that changes every
request goes at the end.**

That is the whole rule. It is worth being precise about what "the front" means,
because it is not the front of your Python list.

Providers assemble the prompt in a fixed order before they look for a cached
prefix. Tool definitions come first, then the system prompt, then the messages
oldest to newest. Your job is to make sure that everything early in that assembled
order is byte identical from one request to the next, and that everything which
varies lands after it.

The match is a prefix match on bytes. Not a similarity score, not a fuzzy match.
The first byte that differs ends the reusable region, and everything after that
byte is processed from scratch, however much of it was identical.

### The failure, measured

Here is the experiment. It uses the real tool schemas and the real system prompt
from this folder, builds the assembled prefix in the order above, and measures
how much of it two consecutive requests share. Paste it into a file in this
folder and run it.

```python
import json
import os
import random

os.environ["AGENTPATH_WORKSPACE"] = "."
import prompt
import tools

SCHEMAS = [{"type": "function", "function": t["function"]} for t in tools.SCHEMAS]
SYSTEM = prompt.build_system_prompt(os.getcwd())
HISTORY = []
for i in range(6):
    HISTORY.append({"role": "user", "content": f"question {i} " * 20})
    HISTORY.append({"role": "assistant", "content": f"answer {i} " * 60})


def prefix(schemas, system, newest):
    parts = [json.dumps(s) for s in schemas]
    parts.append(system)
    parts += [json.dumps(m) for m in HISTORY]
    parts.append(json.dumps({"role": "user", "content": newest}))
    return "".join(parts)


def shared(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def report(label, first, second):
    n = shared(first, second)
    print(f"{label:24} {n:6} of {len(first)} chars reusable, {100 * n / len(first):5.1f}%")


good_1 = prefix(SCHEMAS, SYSTEM, "and now the seventh question")
good_2 = prefix(SCHEMAS, SYSTEM, "and now the eighth question")
report("stable content first", good_1, good_2)

stamped_1 = prefix(SCHEMAS, "Session 8f21a0c4. Time 2026-09-01T09:14:03Z.\n" + SYSTEM, "and now the seventh question")
stamped_2 = prefix(SCHEMAS, "Session 1d0b77e9. Time 2026-09-01T09:14:41Z.\n" + SYSTEM, "and now the eighth question")
report("stamp in the system", stamped_1, stamped_2)

shuffled = list(SCHEMAS)
random.Random(3).shuffle(shuffled)
report("schemas reordered", good_1, prefix(shuffled, SYSTEM, "and now the eighth question"))
```

```text
stable content first       8196 of 8214 chars reusable,  99.8%
stamp in the system        2589 of 8259 chars reusable,  31.3%
schemas reordered           307 of 8214 chars reusable,   3.7%
```

Three lines, and each one is a different lesson.

**99.8 percent.** With the stable content genuinely stable, the only thing that
differs between two consecutive requests is the newest user message. Everything
before it is reusable. This is what you are trying to have.

**31.3 percent.** One session identifier and one timestamp, forty four characters
of them, at the top of a system prompt. The tool schemas in front of them still
match, which is the only reason this is 31 percent rather than nothing, and every
byte after them is lost. The system prompt is lost. The entire twelve message
history is lost. Six turns of conversation that were identical in both requests
are reprocessed at full price because of forty four characters that nobody was
even reading.

**3.7 percent.** The tool schemas in a different order. Same seven tools, same
descriptions, same JSON schemas, nothing removed and nothing added. The list is
in a different order, so the second schema's first byte differs, and everything
from there to the end of the request is a cache miss. That is 96 percent of the
request reprocessed because a list got shuffled.

### The four things that do this to you

**A timestamp.** Somebody adds `The current time is {datetime.now()}` to
`build_system_prompt`, for a good reason, because models are bad at knowing the
date. It is now the most expensive line in your program.

**A session identifier.** Same shape. `Session {session_id}` near the top of the
system prompt so that logs correlate. Every session gets a different one, so
every session begins from a cold cache no matter how similar the work is, and
within a session anything that regenerates the identifier per request destroys
the cache on every single call.

**A user name, or anything else per user.** `You are helping {user}` at the top
of a system prompt is the same failure with a slower fuse. It does not hurt while
you are testing with one account. It quietly gives you a separate cold cache per
user in production, which is the point at which it costs the most.

**Tool definitions in a nondeterministic order.** This one is the nastiest,
because you did not write the bug and it may not be reproducible on your machine.
Build your tool list from a `set`, or from a plugin loader that walks a directory,
or from a dictionary you mutate at import time, and the order is stable within one
process and different on the next start, or different between two workers behind
a load balancer. The 3.7 percent line above is what each of those costs.

Whitespace and key order in your JSON belong on the same list. Two schemas that
are semantically identical but serialised with different key ordering are two
different byte strings, and the comparison is on bytes.

### Why this is worse than an ordinary bug

Nothing errors.

There is no exception. There is no warning. The response is correct, the agent
behaves exactly as it did yesterday, every test passes, and every log line looks
normal. The only symptom is that the bill is two or three times what it was, and
the bill arrives at the end of the month with no per request breakdown that would
point at a line of Python.

This is the reason the section is this long. A failure that crashes teaches you
where it is. A failure that only costs money has to be looked for on purpose,
which means you have to already know it exists. That is what you are reading
this for.

### How to actually find out

The reported usage tells you, and this is the payoff for `per_call` keeping the
whole dictionary in section 3.

Providers report cached tokens as their own fields alongside the input count.
Anthropic reports `cache_read_input_tokens` and `cache_creation_input_tokens`.
OpenAI compatible endpoints that support it typically report a `cached_tokens`
figure nested inside `prompt_tokens_details`. Either way, the number you want is
the ratio of cached to total input, per call, across a run.

```python
for index, reported in enumerate(usage.per_call):
    cached = reported.get("cache_read_input_tokens", 0) or (
        reported.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    )
    total = reported.get("prompt_tokens") or reported.get("input_tokens", 0)
    share = 100 * cached / total if total else 0
    print(f"call {index} {cached}/{total} cached, {share:.0f}%")
```

What you are looking for is simple. On a multi turn run with caching enabled, the
first call is a cache write and reads nothing. Every call after it should read
most of its input from cache, and the share should climb as the conversation
grows. If it is zero on every call, something in your prefix is changing and one
of the four items above is the reason. If it starts high and collapses at turn
six, look at what turn six did differently.

Add that loop to your harness once and you will never wonder about this again.

### Two consequences that surprise people

**Caching and trimming are in tension, and lesson 14 was the one that started
it.** `fit_to_budget` drops the oldest exchange. The oldest exchange is at the
front of the messages, which means it is inside the cached prefix, which means
the request after a trim shares almost nothing with the request before it. Every
trim costs you a full cache miss on the next call.

That does not make trimming wrong. It makes the shape of trimming matter. Trim
rarely and in large chunks rather than constantly and in small ones, because ten
small trims are ten cache misses and one large trim is one. If `fit_to_budget` is
called with a budget just below the current size, it will shave one block off
every turn forever, and that is close to the worst case available to you. Trim
down to well below the budget when you trim at all, so the next several turns can
run cached.

**There is a floor, and short prompts do not cache.** Providers only cache
prefixes above a minimum length, on the order of a thousand tokens. Below that
the bookkeeping is not worth it, and the request quietly does not cache with no
indication that it did not. If you are testing caching with a tiny system prompt
and two messages and seeing no cache reads, that is why, and the code is
probably fine.

---

## 6. Other savings worth having, in order of effect

Caching is first because it is free. Everything in this section costs you
something, usually a little capability or a little complexity, so they are
ordered by how much they return for what they take.

### One. Do not read a whole file when a grep and a targeted read would do

The measurement, from this folder.

```python
import os

os.environ["AGENTPATH_WORKSPACE"] = "."
import tools

whole = tools.run("read_file", {"path": "tools.py"})
found = tools.run("grep_files", {"pattern": "def truncate", "glob": "*.py"})
print(len(whole), len(found))
```

```text
4035 50
```

Four thousand and thirty five characters against fifty. About a thousand tokens
against a dozen. And `tools.py` is 13,372 characters, so the four thousand is
already what is left after `truncate` cut it, which means the agent got a third of
the file and a note saying `[truncated, 9372 more characters]`.

Now remember section 2. That thousand tokens does not cost you once. It sits in
the conversation and is resent on every subsequent request for the rest of the
session. Read six files early in a task and you have added six thousand tokens to
the floor of every request that follows.

The habit is the one lesson 09 argued for on different grounds. Find the thing
first, then read around it. `grep_files` returns paths and line numbers precisely
so that the next call can be narrow. A `read_file` that takes a line range is
about six lines of change to `tools.py` and it is the single highest value tool
change you can make after this chapter.

The cost of this saving is real and you should name it. An agent that reads
fragments sometimes misses context that was forty lines away, and it will
occasionally make a worse edit because of it. That is a genuine trade rather than
a free win.

### Two. Truncate tool output before it goes back into the conversation

You already have this, and it is one function from lesson 07.

```python
def truncate(text, limit=MAX_OUTPUT):
    """Keep tool output small enough that it does not eat the context window."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[truncated, {len(text) - limit} more characters]"
```

`MAX_OUTPUT` is 4000 and `read_file` applies `truncate` to everything it returns.

Three things about this are worth stating plainly.

**The bound is per result, not per conversation.** `truncate` guarantees that no
single tool result exceeds four thousand characters. It says nothing about the
sum of them, which is what lesson 14 exists to handle and section 1 of this
chapter is complaining about.

**Truncating before the result enters the conversation is the whole point.**
Trimming later, in `fit_to_budget`, happens after you have already paid to send
the oversized result at least once, and possibly several times. `truncate` is
free and it is upstream of the cost. Trimming is not free, because it costs you a
cache miss, and it is downstream.

**Saying that it truncated matters as much as the truncating.** The suffix tells
the model that there is more, and how much more, so it can ask for a different
slice. A truncation the model cannot see is one it will confidently reason past.

### Three. Use a cheaper model for small mechanical tasks

Not every call in a harness needs the model that writes the code. Summarising a
finished exchange, classifying whether a shell command is dangerous, deciding
which of eight files is worth reading, naming a session, extracting a file path
from a sentence. These are mechanical, they are checkable, and a small model does
them about as well.

The arithmetic is straightforward once `Usage` exists, because the same traffic
priced two ways is two calls to `cost`.

```python
from usage import Usage

usage = Usage()
for turn in range(10):
    usage.add({"prompt_tokens": 1400 + 1000 * turn, "completion_tokens": 400})

print(round(usage.cost(3.0, 15.0), 4))
print(round(usage.cost(0.25, 1.25), 4))
```

```text
0.237
0.0198
```

The same 59,000 prompt tokens and 4,000 completion tokens, twelve times apart.

The structural point is more important than the ratio. Your harness has one
provider today, and the moment you want a cheap model for the mechanical calls it
needs two. That is not a problem, because lesson 06 built exactly the interface
this needs. Two instances of `OpenAICompatProvider` with different models, one
passed to `run` and one held by whatever does the summarising, and nothing else
changes.

The cost of this saving is that a small model doing a classification will
sometimes get it wrong, so put it on jobs where a wrong answer is survivable. A
bad session name is a shrug. A bad "is this command dangerous" is a disaster, and
lesson 12 already told you that gate belongs with a human rather than with any
model at all.

### Four. Send only the tool schemas the task could plausibly need

The schemas are part of every request, and this is the item people forget because
the schemas are not in `messages` and therefore are invisible to
`estimate_tokens`.

```python
import json
import os

os.environ["AGENTPATH_WORKSPACE"] = "."
import tools

for schema in tools.SCHEMAS:
    raw = json.dumps({"type": "function", "function": schema["function"]})
    print(f"{schema['function']['name']:12} {len(raw):5} chars")
print(f"{'total':12} {len(json.dumps(tools.SCHEMAS)):5} chars")
```

```text
read_file      264 chars
write_file     429 chars
edit_file      518 chars
list_files     271 chars
run_shell      348 chars
glob_files     329 chars
grep_files     422 chars
total         2595 chars
```

2595 characters, which `cl100k` counts as 649 tokens. Resent on every request,
whether the model uses one of them or none of them. On the ten turn run from
section 2 that is 6,490 tokens of schema, about eleven percent of the whole
prompt bill, for text that never changes.

Two things follow, and they point in opposite directions.

**Cutting schemas is worth doing when the task genuinely cannot use them.** A
read only question does not need `write_file`, `edit_file` or `run_shell`, which
is 1295 characters, half the total. Passing a filtered list to `run` is a one line
change because `schemas` is already computed from `tools.SCHEMAS` in one place.

**Do not do it dynamically, per turn.** Read section 5 again. The tool
definitions are the very first thing in the assembled prefix, so changing the set
of tools between requests is the 3.7 percent line. A harness that helpfully drops
`write_file` on turn four because the task looks read only has just thrown away
the cached prefix for the entire conversation, and the schema tokens it saved are
a rounding error against what that cost.

So choose the tool set once, at the start of a task, from something stable, and
then leave it alone. Same list, same order, every request. If you want a genuinely
large tool catalogue, the answer is not to filter it per turn, it is to give the
model a way to search the catalogue, which keeps the sent set fixed.

### Five. Stop paying for a loop that is not going anywhere

This one is in `agent.py` in this folder and it is new since lesson 14.

```python
            current = signature(call["name"], call["arguments"])
            recent.append(current)
            going_in_circles = recent[-REPEAT_LIMIT:].count(current) >= REPEAT_LIMIT
```

`signature` comes from `permissions.py`, where lesson 12 already needed a stable
string for one exact call, and `REPEAT_LIMIT` is 3. If the last three calls are
the same tool with the same arguments, the model is told so, in words.

```python
                result = (
                    f"Error: {call['name']} has been called with these exact arguments "
                    f"{REPEAT_LIMIT} times in a row and nothing has changed. You are going "
                    "in circles. Stop repeating it and try a different approach."
                )
```

And if it does it again after being warned, the loop stops.

```python
                        f"Stopping. {call['name']} was warned about repeating itself and "
                        "repeated anyway. Continuing would only cost money."
```

**Why this is a cost control rather than a correctness feature.** `max_turns=10`
already bounds the run. What it does not do is notice that nothing is changing.
An agent stuck on the same failing `run_shell` will burn all ten turns, and by
section 2's arithmetic the last of those turns is the most expensive one in the
run. Detecting the loop at turn three saves the seven most expensive requests.

**Why the model is told rather than the call being silently skipped.** Same
argument lesson 12 made about refusals. A model that does not know what happened
cannot choose differently, so it tries again. Telling it plainly gives it a
chance to change course, and the check is only fatal on the second offence, after
it has had that chance.

---

## 7. Turning tokens into money

Tokens are the unit the provider counts in. Money is the unit you make decisions
in. The conversion is one method.

```python
    def cost(self, prompt_price_per_million=0.0, completion_price_per_million=0.0) -> float:
        """Turn tokens into money, given the prices you are actually paying.

        Prices are an argument rather than a table baked into the code
        because they change, and a stale price table is worse than no price
        table since it looks authoritative while being wrong.
        """
        return (
            self.prompt_tokens * prompt_price_per_million
            + self.completion_tokens * completion_price_per_million
        ) / 1_000_000
```

The arithmetic is deliberately trivial. Multiply each count by its price, add
them, divide by a million because that is the unit prices are quoted in.

`check.py` runs it on the four call conversation from section 1.

```python
    price = usage.cost(prompt_price_per_million=3.0, completion_price_per_million=15.0)
```

```text
OK tokens can be turned into money, about 0.000564 at example prices
```

Check it by hand. 68 prompt tokens at 3.0 per million is 204. 24 completion
tokens at 15.0 per million is 360. That is 564, divided by a million, 0.000564.

**Why prompt and completion are priced separately.** Because they are, everywhere.
Output tokens cost several times what input tokens cost, typically around five
times, and that ratio changes what you should optimise. It is the reason an agent
that reads a lot and writes a little has a bill dominated by the input column,
which is why sections 5 and 6 are almost entirely about input.

**Why prices are an argument and not a table in the code.** This is the decision
worth arguing about, because a table would be more convenient and every reader's
first instinct is to add one.

A price table in a file has a property that makes it dangerous rather than merely
imperfect. It looks authoritative. Somebody reading `PRICES["some-model"] = 3.0`
in a source file has no way to tell whether that line was written yesterday or
two years ago, and no reason to doubt it, because it is in the code and the code
works. Prices change. Vendors add tiers. A model gets a cheaper successor with a
similar name. Every one of those makes the table wrong without making it look
wrong, and the number it produces is still a plausible looking float that gets
put into a report.

An argument cannot go stale, because it has no memory. Somebody has to supply it
at the call site, which means somebody has to have looked. Passing `3.0` and
`15.0` is a claim you are making with your eyes open, and if you got it from a
price page six months ago that is at least your six month old claim rather than a
stranger's.

The rule generalises. When a value is outside your control, changes without
telling you, and produces a plausible answer when it is wrong, make the caller
supply it. Reserve defaults for things that are either correct forever or
obviously placeholders. The `0.0` defaults here are the second kind, deliberately,
because a run you forgot to price comes out as zero rather than as a number you
might believe.

**The honest limit.** `cost` knows about two columns and there are more than two.
Cached reads are cheaper than fresh input, cache writes are more expensive, and
some providers bill reasoning tokens separately. As written, a run that got 90
percent cache hits is priced as though it got none, so `cost` overstates. The data
to fix that is already in `usage.per_call` from section 3, and the fix is more
arguments, which is the same design decision applied again rather than a new one.

---

## 8. Running check.py

From the lesson folder, with an endpoint configured, because unlike lesson 14
this check genuinely calls a model. It needs `AGENTPATH_BASE_URL` and
`AGENTPATH_MODEL`.

```bash
cd lessons/15-token-economy
python check.py
```

Or against the built in mock server along with every other lesson, which is what
continuous integration runs.

```bash
python ci/run_lessons.py
```

A passing run prints five lines.

```text
OK the same conversation cost more every turn, [2, 12, 22, 32]
OK usage adds up across calls, 4 calls, 68 prompt tokens, 24 completion tokens
OK tokens can be turned into money, about 0.000564 at example prices
OK putting the unchanging part first leaves a prefix a provider can reuse
OK putting the changing part first destroys that prefix, which is the mistake to avoid
```

Two of those five are the facts the whole chapter rests on, and the docstring at
the top of `check.py` says which.

**One. The growth is demonstrated, not asserted.**

```python
    if prompts != sorted(prompts) or prompts[0] == prompts[-1]:
        fail(f"the prompt cost did not grow every turn. Saw {prompts}")
```

Two conditions, and the second one is the interesting one. `prompts !=
sorted(prompts)` catches a count that ever goes down. `prompts[0] ==
prompts[-1]` catches a count that never goes up, which a provider reporting a
constant, or zero, would satisfy while passing the first test. A monotonic
sequence of four identical numbers is sorted. Asserting that it is sorted proves
nothing on its own.

Note what is not asserted. Nothing here says the numbers should be 2, 12, 22 and
32. Those are what this particular mock produces and a real provider will produce
different ones, so the check asserts the shape rather than the values. The values
are printed, because the point of the line is for you to read them.

**Two. Four calls were counted.**

```python
    if usage.calls != 4:
        fail(f"expected four calls, counted {usage.calls}")
```

Four requests went out, so `Usage` must have recorded four. This is the assertion
that catches the `if not reported: return` guard from section 3 quietly eating
everything, which is exactly what would happen against a provider whose usage
field names do not match.

**Three. The money is a real number.**

```python
    price = usage.cost(prompt_price_per_million=3.0, completion_price_per_million=15.0)
    if price <= 0:
        fail("turning tokens into money produced nothing")
```

Greater than zero rather than equal to a specific figure, for the same reason as
above. The exact value depends on what the provider counted.

**Four and five. The ordering rule, as two sides of one fact.**

```python
    stable = [{"role": "system", "content": "long instructions " * 20}]
    first = stable + [{"role": "user", "content": "one"}]
    second = stable + [{"role": "user", "content": "two"}]
    shared = 0
    for left, right in zip(first, second):
        if left != right:
            break
        shared += 1
    if shared != 1:
        fail("the unchanging prefix was not shared between two requests")
```

Two requests that differ only in the newest message share their first message
exactly. Then the mirror image.

```python
    moved_first = [{"role": "user", "content": "one"}] + stable
    moved_second = [{"role": "user", "content": "two"}] + stable
    if moved_first[0] == moved_second[0]:
        fail("this check is wrong, the first messages should differ")
```

Same two lists, same contents, changing part moved to the front. Now the very
first element differs and there is no shared prefix at all, even though the long
stable block is still sitting there in both.

These are deliberately at the level of message identity rather than bytes,
because a check that runs on every push should not depend on a provider's
tokeniser or on a cache that may or may not be warm. They prove the structural
claim, which is that ordering determines what two requests have in common. The
byte level version of the same claim, with the 99.8, 31.3 and 3.7 percent
figures, is the script in section 5, and that one you run by hand when you want
to see the size of it.

If the first line ever fails saying the cost did not grow, read the list it
prints before assuming the check is broken. A list of zeros means your provider
is not reporting usage in the stream, and section 3 has the two reasons that
happens. A list that grows and then drops means something is trimming the
conversation between turns.

---

## 9. What you cannot do yet

You can now see what a run costs, you know which number to trust and which number
is only a trigger, and you know the one ordering mistake that silently multiplies
a bill. That is genuinely most of the money.

What you still cannot do is get information into the conversation that was never
in it.

Everything in fifteen lessons assumes the answer is somewhere the agent can reach
by acting. It greps, it reads, it runs a command and reads the output, and every
one of those puts text into the conversation where the model can see it. The
whole economics of this chapter is about that text, how much of it there is, and
how many times you pay to resend it.

But sometimes the answer is not in a file the agent can find by pattern. It is in
four hundred pages of documentation, or two years of design notes, or a support
archive, where no single grep pattern would find the right paragraph and reading
the whole thing would cost more than the answer is worth. `grep_files` is a
superb tool when you know roughly what string you are looking for. It is useless
when the thing you need says the same idea in different words.

That is a different problem and it wants a different mechanism, and it is
also where an enormous amount of money gets wasted by people who reach for that
mechanism first. Lesson 09 promised this argument would be finished properly
rather than waved at, and lesson 16 is where it happens. Four questions in order,
the honest case for not building a retrieval system at all, and then a small
vector index built for real so you can measure the difference on your own
material instead of arguing about it.

Before you go on, do one thing. Run your agent on a real task with a `Usage`
attached, print `usage.summary()` at the end, then run the same task again after
moving anything that varies to the end of your prompt. Write down both numbers.
That comparison is the habit this chapter exists to give you, and it is worth
more than any of the individual facts in it.

On to lesson 16.
