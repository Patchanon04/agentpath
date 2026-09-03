[อ่านภาษาไทย](README.th.md)

# Lesson 21. Multi agent patterns

Lesson 20 gave the agent a way to hand work to another agent. This chapter
builds the machinery for running several jobs at the same time, and then spends
most of its length on the three things that go wrong when you do.

Be clear about the scope before you read further, because the word multi agent
promises more than this chapter delivers. `fanout.py` knows nothing about
agents. It takes a list of labelled callables that produce events, runs them on
a pool of threads, and hands the events back through one queue. Nothing in this
folder wires `run_in_parallel` to `subagent.py` or to `agent.py`, and the checks
drive it with toy jobs that yield strings and sleep, because the concurrency is
the subject and a real model call would only make the behaviour harder to see.
Lesson 22 is the first real caller. Its `run_evals` uses `run_in_parallel` to
put an eval suite across several workers, and that is where this module starts
doing work you would ship.

Here is what is in this folder and where each file came from.

```text
lessons/21-multi-agent/
    fanout.py           new. the subject of this chapter. run_in_parallel, the
                      DONE sentinel, and FanoutError
  grep_worker.py      identical to lesson 20

  check.py            new. four claims about running things at once
  agent.py            identical to lesson 20
  subagent.py         identical to lesson 20
  tools.py            identical to lesson 20
  session.py          identical to lesson 20
  permissions.py      identical to lesson 20
  providers.py        identical to lesson 20
  prompt.py           identical to lesson 20
  context.py          identical to lesson 20
  usage.py            identical to lesson 20
  retrieval.py        identical to lesson 20
  retry.py            identical to lesson 20
  cancel.py           identical to lesson 20
  main.py             identical to lesson 20
  mcp.py              identical to lesson 20
  mock_mcp_server.py  identical to lesson 20
  README.md           this file
```

Every folder from lesson 19 onward carries the whole course, so a chapter can be
opened on its own and run without first copying files in from a neighbour. Two files are new, `fanout.py` and `check.py`, which means sixteen of the
eighteen Python files are byte for byte what they were last chapter. That is
checkable rather than claimed.

```bash
cd lessons
for f in agent.py subagent.py tools.py session.py; do
  diff -qs 20-subagents/$f 21-multi-agent/$f
done
```

```text
Files 20-subagents/agent.py and 21-multi-agent/agent.py are identical
Files 20-subagents/subagent.py and 21-multi-agent/subagent.py are identical
Files 20-subagents/tools.py and 21-multi-agent/tools.py are identical
Files 20-subagents/session.py and 21-multi-agent/session.py are identical
```

`agent.py` did not change. That is worth noticing before you read another word.
Running four agents at once is not a change to the agent loop. It is a change to
who calls the loop and how many times at once, which is why it arrives as one
new module and no edits anywhere else.

## 1. The problem left over from lesson 20

Lesson 20 built `run_subagent`. The parent asks for a job, a fresh agent runs it
with its own context, and the parent gets back an answer instead of a
transcript. The context problem from lesson 18 is solved. Something else is not.

Look at where a subagent call is actually dispatched. It is inside the loop in
`agent.py`, in the same place every other tool call is dispatched.

```python
        for call in calls:
            if stop_requested():
                raise KeyboardInterrupt("cancelled")
            ...
            result = tools.run(call["name"], call["arguments"])
```

`for call in calls` is a plain Python loop over a list. It runs the first call,
waits for it to return a string, then runs the second. That is exactly right for
`read_file`, which takes a millisecond. It is exactly wrong for `run_subagent`,
which starts a whole agent that will make several provider requests and wait on
each one.

Make it concrete. You ask the agent to review four modules and report on each.
It emits four `run_subagent` calls in one turn. Each child takes about forty
seconds, most of that spent waiting for a response to arrive over a socket.

```text
worker one    [========================================]  40s
worker two                                              [========================================]  40s
worker three                                                                                      [====...
worker four                                                                                             ...
                                                                                        total 160 seconds
```

None of the four needs anything from the other three. They read different files,
answer different questions and produce independent answers. There is no data
dependency anywhere in that picture, and yet the fourth one starts two minutes
after it could have. The machine is not busy during those two minutes. It is
idle, holding four open sockets one at a time.

That is the whole problem this chapter fixes, and it is worth being precise
about what kind of problem it is. It is not a correctness problem. The four
answers you get at the end of the sequential version are exactly the answers you
get from the parallel version. It is a latency problem, and latency is what
decides whether a person leaves the agent running or gives up and does the work
themselves.

So the goal for this chapter is one function. Hand it a list of independent
jobs, get back the events from all of them as they arrive, in whatever order
they arrive, each one labelled with the job that produced it.

## 2. Why threads and not async

Before any code, the decision that shapes all of it.

The choice starts from the fact that Python offers at least two ways to have
several things in flight at once. Threads, where the operating system
schedules several stacks and switches between them, and `asyncio`, where one
stack runs an event loop and functions marked `async` hand control back at
every `await`. There is also multiprocessing, which is a third thing and is
not a candidate here for a reason given below.

This project uses threads, and the reason is in what an agent run actually
spends its time doing. It builds a request, sends it, and then waits. It waits
for the first byte of the response. It waits for each chunk of the stream.
Between turns it runs a tool, which is usually a file read or a subprocess,
and then it waits again. Almost the entire wall clock life of an agent run is
time spent blocked on a socket with nothing to compute.

That is the exact case threads handle well. A blocked thread costs you a stack
and a scheduler entry and nothing else. The global interpreter lock, which is
the thing people correctly warn you about, is released while a thread is waiting
on I/O, so four threads waiting on four sockets really do wait at the same time.
The lock only serialises threads that are running Python bytecode, and an agent
run does very little of that.

This is also why multiprocessing is not the answer. Processes exist to get
around the interpreter lock for work that is genuinely CPU bound. Paying for
four interpreters, four copies of every import, and pickling every message
across a pipe, in order to speed up four things that are all asleep on a socket,
is buying an expensive solution to a problem you do not have.

We are not using async, given that async exists for precisely this, because of
what it would cost the reader rather than what it would cost the machine.

Every module in this project is synchronous. `providers.py` calls `httpx` and
blocks. `tools.py` calls `subprocess.Popen` and waits in `communicate`. `agent.py` is an ordinary
`for` loop calling ordinary functions. Introducing `asyncio` here does not add a
keyword. It changes the colour of every function it touches, and the change
spreads outward. `run_in_parallel` becomes `async def`. To await inside it, the
agent run must be awaitable, so `run` becomes `async def`. To await inside that,
`provider.stream` becomes `async def`, which means `httpx.Client` becomes
`httpx.AsyncClient`, which means the generator that yields streamed text becomes
an async generator, which means every `for` over it becomes `async for`. The
tools still block, so they need `run_in_executor`, which puts a thread pool back
into the program anyway. And every `check.py` in the repository needs an event
loop to call anything.

The reader came here to learn how agents work. Making them learn the colour rule
first, and debug a hang caused by one forgotten `await`, is a real cost paid in
the wrong currency. Threads let this chapter be about fan out, ordering,
failure and shared state, which are the ideas that transfer, rather than about
Python's concurrency syntax, which does not transfer anywhere.

The honest version of the claim is that threads are not better than async. A
service running thousands of concurrent agents would use async, and would be
right to. At that scale the per thread stack cost and the context switching stop
being noise, and an event loop holding ten thousand idle sockets is
straightforwardly cheaper than ten thousand threads holding the same sockets.
The number where that crossover happens is somewhere in the high hundreds, and
this chapter runs four workers.

So this is a teaching decision, stated as one. If you take this code into a
service that fans out to hundreds of agents per process, rewrite it with
`asyncio`. The queue, the sentinel, the labelling and every problem in sections
4 through 8 survive that rewrite unchanged, because none of them is about
threads. They are about several things happening at once, which is true in
either model.

The module docstring says the same thing in five lines.

```python
"""Running several agents at once and merging what they say.

Threads rather than async, for the same reason the rest of the project is
synchronous. An agent run spends nearly all of its life waiting on a socket,
which is the case threads handle well, and async would put a second mental
model in front of a reader who came here to learn about agents.
"""
```

## 3. One queue as the meeting point

Here is the whole of `run_in_parallel`.

```python
def run_in_parallel(jobs, workers=4):
    jobs = list(jobs)
    if not jobs:
        return

    results = queue.Queue()
    pending = queue.Queue()
    for job in jobs:
        pending.put(job)

    def work():
        while True:
            try:
                label, produce = pending.get_nowait()
            except queue.Empty:
                return
            try:
                for event in produce():
                    results.put((label, event))
            except Exception as error:
                results.put((label, FanoutError(label, error)))
            finally:
                results.put((label, DONE))

    threads = [
        threading.Thread(target=work, daemon=True) for _ in range(min(workers, len(jobs)))
    ]
    for thread in threads:
        thread.start()

    finished = 0
    while finished < len(jobs):
        label, event = results.get()
        if event is DONE:
            finished += 1
            continue
        yield label, event

    for thread in threads:
        thread.join()
```

Forty lines. Take them in the order they matter.

### What a job is

```python
    jobs = list(jobs)
```

A job is a pair of a label and a callable that returns an iterator of events. The
label is a string you chose, like `"auth"` or `"parser"`. The callable takes no
arguments and, when called, produces events one at a time.

Why a callable rather than an iterator. Because the iterator must be created
inside the worker thread, not in the caller. If you passed an already started
generator, the caller would have run the first part of it on the main thread
before handing it over, which quietly defeats the point and makes the timing
impossible to reason about. Passing a function means nothing about the job has
happened until a worker picks it up.

Why `list(jobs)` on the first line. Because the function needs `len(jobs)`
twice, once to size the thread pool and once as the loop bound, and a caller is
allowed to pass a generator. Calling `len` on a generator raises, and iterating
it twice yields nothing the second time. One line removes both failures.

And the empty case returns immediately, because starting zero threads and then
waiting for zero sentinels would work but reads as if it might not.

### The pending queue, which is the work

```python
    pending = queue.Queue()
    for job in jobs:
        pending.put(job)
```

Every job goes into a queue before any thread starts. Then each worker pulls
from it in a loop until the queue is empty.

Why a queue and not one thread per job. Two reasons, and the second is the real
one. Ten jobs would mean ten threads, a hundred jobs a hundred threads, and the
`workers` parameter would be a lie. More importantly, the number of agents you
run at once is a rate limit question. Providers throttle by requests per minute,
and a fan out that starts sixty agents because you happened to have sixty files
will collect sixty 429s. `workers=4` is a valve, and a shared queue is what makes
the valve real.

Why `get_nowait` rather than `get`. Because an empty pending queue means the
work is finished, and this worker should return. A blocking `get` would wait
forever for a job that is never coming, and the thread would never exit. The
alternative is a sentinel per worker pushed onto `pending`, which works and is
more code for the same effect. `get_nowait` plus catching `queue.Empty` says the
same thing in three lines.

This design has a property worth naming. Jobs are not assigned to workers in
advance. A worker that finishes a fast job immediately takes the next one, so
three quick jobs and one slow one do not leave three threads idle while the slow
one runs. Static assignment, where worker one gets jobs one and two and worker
two gets three and four, is simpler and is worse for exactly this reason.

### The results queue, which is the answers

```python
                for event in produce():
                    results.put((label, event))
```

Every event goes onto one queue, and it goes on paired with its label. There is
one results queue for the whole fan out, not one per job.

Why one queue. Because the caller wants events as they arrive, and merging four
queues means polling four queues, which means either a spin loop or four extra
threads to do the merging. A single queue does the merge for free, and
`queue.Queue` is the standard library's thread safe handoff, so nothing in this
file takes a lock explicitly.

Why the label travels with every single event rather than being announced once
at the start of a job. Because there is no start of a job on the receiving end.
Events from four jobs arrive shuffled together, so a marker saying the next
events belong to `auth` would be immediately followed by three events that do
not. Section 4 is entirely about the consequences of this, and the labelling is
the thing that makes the consequences survivable.

### The sentinel that says a worker finished

```python
DONE = object()
```

One line at the top of the module. A bare `object()`, used only for its
identity, and compared with `is` rather than `==`.

Why a sentinel at all. The consumer needs to know when to stop reading from the
results queue. It cannot know from the queue itself, because an empty queue
means nothing. It could mean a worker is between events. So completion has to be
announced in band, as a value, and that value is `DONE`.

Why `object()` rather than `None`, or the string `"done"`, or a `StopIteration`.
Because the sentinel must not be a value any job could legitimately produce. A
job that yields `None` is entirely plausible. A job that yields the string
`"done"` is plausible in a chapter about agents reporting on their work. A
freshly made `object()` has no other reference anywhere in the program, so
`event is DONE` is true for exactly one thing in the universe and cannot be
faked by a payload.

Now the placement, which is the part that carries the weight.

```python
            finally:
                results.put((label, DONE))
```

It is in a `finally`. A job that completes normally puts a `DONE`. A job that
raises puts a `FanoutError` and then a `DONE`. There is no path through the
worker's body that consumes a job from `pending` without eventually putting a
`DONE` on `results`. That invariant is the only thing standing between the
caller and a permanent hang, so it is enforced by the language rather than by
remembering to do it in two places.

Notice also that `DONE` is per job and not per worker. It is inside the `while`
loop, so a worker that handles three jobs emits three sentinels. That is what
makes the counting in the next part correct.

### Why the main loop counts sentinels

```python
    finished = 0
    while finished < len(jobs):
        label, event = results.get()
        if event is DONE:
            finished += 1
            continue
        yield label, event
```

The termination condition is that the number of sentinels seen equals the number
of jobs submitted. Not that the threads have stopped.

The obvious alternative is to ask the threads.

```python
    while any(thread.is_alive() for thread in threads):
        ...
```

That is wrong in both directions, and both are worth understanding because this
is the classic mistake in producer and consumer code.

It can stop too early. A thread finishes its last job, puts its last events
onto `results`, and exits. Now `is_alive` is false for every thread while events
are still sitting in the queue, unread. The loop exits, and the caller silently
receives fewer events than the jobs produced. Silently is the important word.
Nothing raises. You get an answer that is missing a paragraph and no indication
that anything went wrong.

It cannot stop at the right moment either. `results.get()` blocks. Mixing a
blocking read with a liveness condition means you cannot check the condition
while blocked, so you would need `get(timeout=...)` and a loop that wakes up
repeatedly to ask a question whose answer is almost always the same. That is a
spin loop with extra steps, it burns CPU while doing nothing, and it introduces
a tuning parameter with no correct value.

Counting sentinels has neither problem. `results.get()` blocks with no timeout,
which costs nothing while waiting and wakes the instant something arrives. And
because every job is guaranteed exactly one sentinel by the `finally`, the count
reaching `len(jobs)` means every event that will ever be produced has already
been put on the queue, and every one of them was read before its sentinel,
because each worker put a job's events on the queue before it put that job's
sentinel and the queue hands things back in the order they went in.

There is a deeper point here. `is_alive` answers a question about workers. The
caller's question is about jobs. Those are different things, they are not even
the same in number, and building the loop on the wrong one is what makes the
bug possible in the first place.

The `join` at the end is bookkeeping rather than synchronisation. By the time
the count is reached the work is done, and the join simply reaps the threads so
they do not outlive the call.

### Two honest limits of this function

Neither is a defect, but you should know both.

`run_in_parallel` is a generator, so the threads do not start until the caller
begins iterating. Call it and throw away the result and nothing runs at all.
That is usually what you want and it is occasionally surprising.

And if the caller abandons the generator half way, by breaking out of the `for`,
the threads keep going. They are `daemon=True`, so they will not stop the
program exiting, and the events they produce pile up in a queue nobody is
reading. The `join` at the bottom never runs. For a fan out of four jobs this is
harmless. For a long running service it is a leak, and the fix is a cancellation
token of the kind lesson 17 built, checked by the worker between events.

## 4. Streaming and concurrency pull against each other

This section is not an aside. It is the reason `run_in_parallel` yields
`(label, event)` instead of `event`, and it is the design problem that every
real agent interface has had to solve.

Streaming is for the person watching, and lesson 05 built it on exactly that
argument. A model takes twenty seconds to produce an answer. Printing the
whole thing at the end means twenty seconds of blank screen, and a blank screen
is indistinguishable from a hang. Printing each token as it arrives means the
person sees progress immediately and can tell within two seconds whether the
agent understood the question.

Concurrency breaks that, because streaming works only while there is one writer
to one screen. Four agents streaming at once are four writers to one screen, and
they take turns at character granularity.

This is not a thought experiment. Two jobs, each yielding one character at a
time, written straight to stdout with no label.

```python
jobs = [
    ("one", chars("the auth module looks fine", 0.004)),
    ("two", chars("THE PARSER DROPS A TOKEN", 0.004)),
]
for label, event in run_in_parallel(jobs, workers=2):
    sys.stdout.write(event)
```

```text
tTHhEe  PauAtRSh EmRo dDRulOPeS l Ao oTkOsK EfNine
```

Both sentences are in there. Neither is readable. And notice which one you
lost, because it matters. One of those two jobs was reporting a bug in the
parser, and that is now a sequence of capital letters wedged inside a sentence
saying everything is fine.

Two agents is already unreadable. Four is worse, and the failure is not
graceful. It does not get harder to read, it stops being text.

Every event carries a label because the merge has to be undoable. Once
four streams are concatenated into one character sequence, no amount of cleverness
downstream separates them again. The information about which job said what has
to survive the merge, and the only place to put it is on each event, at the
moment the event is produced, inside the worker that knows the answer.

```python
                for event in produce():
                    results.put((label, event))
```

That is the whole mechanism. `label` is captured from the job the worker pulled
from `pending`, so it cannot get out of step with the events.

With labels the same run is completely readable, and this is real output from
the same three job fan out with a small pause between events.

```text
   c | c-0
   b | b-0
   a | a-0
   b | b-1
   a | a-1
   c | c-1
   c | c-2
   a | a-2
   b | b-2
```

Nine events, thoroughly shuffled, and every one of them attributable.

A real interface stops streaming anyway. Labelling makes the output
recoverable. It does not make token by token text readable. Prefixing every
token with a job name turns twenty five characters of prose into twenty five
lines, which is worse than the interleaving it fixed.

So the answer that actually works, and it is what every serious harness does, is
to change what is displayed the moment more than one job is running. One job,
stream the text. More than one job, stop streaming the text and show progress
per job instead.

```text
  auth      running   3 tool calls   12s
  parser    running   5 tool calls   14s
  storage   done      2 tool calls    9s   found 1 issue
  config    queued
```

That display is built from exactly the same labelled event stream. Nothing in
`fanout.py` changes. The caller is deciding to render one line per label,
updating in place, rather than concatenating text. This is why `run_in_parallel`
takes no opinion about presentation and just yields pairs. The module's job is
to make the information available with its origin attached. What to do with it
is a question about a screen, and a module that printed would have baked one
answer to that question into a file that four threads import.

That is the same argument lesson 18 made about `on_message` being a callback,
and the same one lesson 17 made about the retry helper not printing. It arrives
here as a consequence rather than a preference. A module that prints cannot be
used by four threads at once, because four modules printing to the same stream
produce exactly the nonsense above.

## 5. What is promised and what is not

Two sentences, and the second one is a limit that cannot be lifted.

Order within one job is preserved. If job `auth` produces three events, the
caller receives those three events in that order relative to each other. Always.

Order across jobs is undefined. There is no guarantee about where `auth`'s
events fall relative to `parser`'s, and there cannot be one, because running at
the same time is precisely what it means for two orderings to be unrelated. A
fan out that promised a fixed order across jobs would have to run the jobs one
after another to keep the promise, which is the thing this module exists to stop
doing.

Why the first guarantee holds is worth a sentence, because it is not an accident
of timing. A worker runs `for event in produce()` and puts each event on the
queue in the order it comes out of the iterator. `queue.Queue` is first in first
out. So two events from the same job cannot swap places, because they were put
on the same queue by the same thread in order. Nothing else about the
scheduling matters.

The docstring commits to both, including the part about which one matters.

```python
    jobs is a list of (label, callable) where the callable returns an
    iterator of events. Order across jobs is not defined and cannot be,
    because that is what running at the same time means. Order within one
    job is preserved, which is the part that actually matters.
```

That last clause is the design claim. A job's own events are a sequence with
meaning. Read the file, then edit it, then run the tests. Reversing those is a
different story. Whether `auth` finished before `parser` is almost never
information anybody needs, and the price of guaranteeing it is all of the
speedup.

### The check that proves it

`check.py` runs three jobs of three events each and then asserts on the
per label subsequence.

```python
    jobs = [("a", steps("a", 3)), ("b", steps("b", 3)), ("c", steps("c", 3))]
    seen = list(run_in_parallel(jobs, workers=3))
    if len(seen) != 9:
        fail(f"expected nine events, got {len(seen)}")
    print("OK three jobs ran at once and every event arrived")

    for label in ["a", "b", "c"]:
        ordered = [event for name, event in seen if name == label]
        if ordered != [f"{label}-0", f"{label}-1", f"{label}-2"]:
            fail(f"job {label} came back out of order. Got {ordered}")
    print("OK each job kept its own order even though the output was interleaved")
```

Read what that filter does. It takes the full arrival order, which is shuffled,
and keeps only the events with one label. That subsequence must be exactly
`a-0`, `a-1`, `a-2`. The check asserts nothing whatsoever about where those three
sat in the overall list.

That is the only shape of assertion that can be made here. A check that asserted
on the full list would be asserting on the scheduler, and it would pass on your
machine, pass a hundred times in a row, and then fail in CI on a loaded runner
for reasons that have nothing to do with your code. A flaky check is worse than
no check, because it trains everyone to re run it rather than read it.

The first claim, `len(seen) != 9`, is the counterpart. It says nothing was lost.
That is the assertion that catches the `is_alive` bug from section 3, where a
consumer stops while events are still queued. Nine events went in, nine came
out, and the ordering assertion covers the rest.

Both lines from a real run.

```text
OK three jobs ran at once and every event arrived
OK each job kept its own order even though the output was interleaved
```

One more thing you can see for yourself. Run the same three jobs with no pause
between events and the output often does not interleave at all.

```text
   a | a-0
   a | a-1
   a | a-2
   b | b-0
   b | b-1
   b | b-2
```

Nothing is wrong. The jobs are so short that the first worker drains its entire
job before the operating system has finished starting the third thread. This is
the practical reason the check filters by label instead of expecting a shuffle.
Concurrency does not promise you interleaving either. It only refuses to promise
you order.

## 6. One job failing must not take the batch

When a job raises, the worker catches it, converts it into a value, and puts
that value on the results queue like any other event.

```python
            try:
                for event in produce():
                    results.put((label, event))
            except Exception as error:
                results.put((label, FanoutError(label, error)))
            finally:
                results.put((label, DONE))
```

Three things follow from those seven lines, and each is deliberate.

The other three jobs are untouched. They are running on other threads and know
nothing about this. Their events keep arriving and their sentinels keep the
count moving.

The events this job produced before it broke are already delivered. They went on
the queue as they were produced, so a job that read two files and then failed on
the third has given you two real results plus a report of the failure, rather
than nothing.

And the `finally` still runs, so the sentinel still arrives. Without it, one
raising job would leave the main loop waiting forever for a count that can never
be reached. A batch that hangs on one bad job is a worse outcome than the batch
failing outright, because at least a failure tells you something.

The failure is an event and not an exception. This is the decision worth
defending, because raising it looks more natural and is what most people write
first.

An exception in a worker thread cannot be raised in the caller. There is no
mechanism for it. The best you can do is store it and re raise it from the main
loop, and then answer the question of what happens to the other three jobs.

If you re raise immediately, you have built a fan out where one failure discards
three good results. Four agents reviewed four modules, one of them hit a network
error on its last request, and now you have nothing. The three that succeeded
did succeed, their answers are correct and complete, and you threw them away
because something unrelated went wrong.

If you collect exceptions and raise at the end, you have to invent a way to
raise four things at once, and the caller loses the interleaving that was the
point of streaming results as they arrive.

If you swallow it silently, you get the worst outcome in the whole chapter. Four
jobs go in, three answers come out, nothing anywhere says a fourth job existed.
The caller writes a report on three modules and never learns that the fourth was
never reviewed. The docstring names this directly.

```python
    A job that raises does not stop the others. It yields one final event of
    its own describing the failure, because a batch where one item silently
    vanished is worse than one that reports a problem.
```

Reporting the failure as an event dodges all three. The caller sees it in the
stream, in order, with the label attached, and decides for itself whether a
partial batch is usable. That decision belongs to the caller because only the
caller knows what the batch was for.

**Why `FanoutError` is not an exception class.**

```python
class FanoutError:
    """One job failed. Reported as an event so the caller sees it in order."""

    def __init__(self, label, error):
        self.label = label
        self.error = error

    def __repr__(self):
        return f"FanoutError({self.label!r}, {self.error!r})"
```

It does not inherit from `Exception`. That is not an oversight. It means nobody
downstream can accidentally `raise` it, because Python refuses to raise
something that is not a `BaseException`. The type system enforces that this
thing is a value describing a failure rather than a failure in flight, which is
exactly the distinction the design depends on.

It keeps the original exception in `self.error`, so nothing is lost. The
traceback's type and message are both there for a caller that wants to log them,
and `__repr__` prints both when a check fails, which is the difference between a
useful failure message and `<FanoutError object at 0x7f...>`.

The check is one healthy job and one that breaks half way through.

```python
    def explode():
        yield "before"
        raise RuntimeError("this job broke")

    mixed = list(run_in_parallel([("good", steps("good", 2)), ("bad", explode)], workers=2))
    good = [event for label, event in mixed if label == "good"]
    bad = [event for label, event in mixed if label == "bad"]
    if good != ["good-0", "good-1"]:
        fail(f"a failing job disturbed a healthy one. Got {good}")
    if not isinstance(bad[-1], FanoutError):
        fail(f"a failing job was not reported. Got {bad}")
```

`explode` yields one event before raising, which is deliberate. A job that fails
before producing anything would not test whether partial results survive.

Two assertions, covering the two ways this goes wrong. The healthy job must have
delivered both its events, in order, which rules out the failure disturbing it.
And the last event from the failing job must be a `FanoutError`, which rules out
the silent vanishing. Note that it checks `bad[-1]` rather than `bad`, because
`before` is legitimately in there and must be.

```text
OK one job failing did not take the batch with it, and the failure was reported
```

## 7. Proving the work really overlaps

Everything above is machinery. None of it is worth a line of code if the jobs do
not actually run at the same time, and it is entirely possible to write all of
this and still have it run sequentially, for example by accidentally consuming
each iterator on the main thread.

So the check measures.

```python
    slow = [("x", steps("x", 1, pause=0.3)), ("y", steps("y", 1, pause=0.3))]
    started = time.monotonic()
    list(run_in_parallel(slow, workers=2))
    elapsed = time.monotonic() - started
    if elapsed > 0.55:
        fail(f"the jobs ran one after another, taking {elapsed:.2f} seconds")
    print(f"OK two jobs that each wait 0.3 seconds finished in {elapsed:.2f}, so they overlapped")
```

Two jobs. Each sleeps three tenths of a second and then yields one event. Run
one after another that is six tenths. Run at the same time it is three tenths
plus the cost of starting a thread.

The real output.

```text
OK two jobs that each wait 0.3 seconds finished in 0.30, so they overlapped
```

Three tenths, not six. The overlap is measured rather than asserted, and this is
the only claim in `check.py` that could not be made by reading the code.

Three details in those seven lines are worth copying into your own tests.

The measurement uses `time.monotonic` and not `time.time`. `time.time` is a
wall clock. It can be adjusted by NTP, it jumps when the system clock is
corrected, and it can move backwards, which produces a negative duration and a
check that fails for reasons that have nothing to do with the code.
`time.monotonic` only ever moves forward and exists for exactly this
measurement. Lesson 18's second exercise made the same distinction from the
other direction.

The jobs sleep rather than compute. `time.sleep` releases the interpreter
lock, which makes it an honest stand in for waiting on a socket. Two threads
doing three tenths of a second of arithmetic would not finish in three tenths,
because the lock serialises bytecode. Using a busy loop here would produce a
check that fails while the code is correct, and would be modelling the wrong
thing, since an agent run waits far more than it computes.

The threshold is 0.55 and not 0.31. The bound has to separate the two
outcomes, which are three tenths and six tenths, and it should sit between them
rather than hugging the good one. Thread startup, scheduler jitter and a loaded
CI machine all add milliseconds that have nothing to do with correctness.
Asserting `elapsed < 0.31` gives you a check that fails on a busy afternoon and
teaches everyone to ignore it. Asserting `elapsed > 0.55` fails only if the jobs
genuinely ran one after another, which is the thing being tested.

That last point generalises. When you time concurrency, pick the threshold by
asking which two outcomes you are distinguishing, then put the line in the gap.

## 8. The danger nobody warns you about

Everything so far has been about merging output. This section is about shared
state, it is the reason parallel agents are harder than parallel HTTP requests,
and it is the part that most writing on this subject leaves out.

The concrete failure is this. Two agents are running at the same time. Both have
`edit_file`. Both decide to change `settings.py`.

1. Worker one reads `settings.py`. It now holds the text in its context.
2. Worker two reads `settings.py`. It holds the same text.
3. Worker one works out its change and writes the file. `DEBUG = True` is now on
   disk.
4. Worker two works out its change and writes the file. But worker two is
   writing the version it read in step 2, which does not contain worker one's
   change, plus its own edit on top.

Worker one's change is gone. Not conflicted, not reported, not rejected. Gone,
overwritten by a write that succeeded.

This is the lost update problem, it is decades old, and it is worth watching it
happen. Two jobs, each reading the file, thinking for a moment, and writing.

```python
def editor(label, old, new, pause):
    def produce():
        text = target.read_text(encoding="utf-8")   # read
        yield f"{label} read the file"
        time.sleep(pause)                            # think
        text = text.replace(old, new)
        target.write_text(text, encoding="utf-8")    # write
        yield f"{label} wrote the file"
    return produce

jobs = [
    ("worker-1", editor("worker-1", "DEBUG = False", "DEBUG = True", 0.05)),
    ("worker-2", editor("worker-2", "TIMEOUT = 30", "TIMEOUT = 60", 0.10)),
]
```

The file starts as `DEBUG = False` and `TIMEOUT = 30`. The two workers edit
different lines, which is the case everybody assumes is safe. Real output.

```text
 worker-2 | worker-2 read the file
 worker-1 | worker-1 read the file
 worker-1 | worker-1 wrote the file
 worker-2 | worker-2 wrote the file
---- settings.py afterwards ----
DEBUG = False
TIMEOUT = 60
```

Read the last two lines. `TIMEOUT` was changed. `DEBUG` was not. Worker one
reported success, `edit_file` returned normally, and its change is not on disk.

Sit with how bad the diagnostics are. There is no exception. There is no warning.
Both agents will tell you, honestly, that they made their change, because from
inside each agent that is exactly what happened. The session file records two
successful edits. The only way to find out is to read the file afterwards and
notice something is missing, and if the missing thing is a line you added rather
than a line you removed, you may not notice for a week.

Editing different lines does not save you, because `edit_file` does not edit a
line. It reads the whole file, replaces a string, and writes the whole
file back. The unit of the write is the file, so any two writes to the same file
collide regardless of how far apart the changes are. The example above is the
friendliest possible version of this, two independent one line changes, and it
still lost one.

It is not theoretical, and it is not rare. It needs two conditions. Two
agents running at the same time, and any overlap in the files they touch. Fan
out over four modules in one package and they will all want to touch the shared
config, the imports, the test helpers. The more useful your fan out is, the more
the jobs are related, and the more related they are the more they overlap.

Real harnesses answer this in two families, and both are real engineering
rather than a flag.

The first is to serialise the writes. Reads run in parallel because concurrent
reads cannot conflict, and every tool that mutates the world goes through a lock
or a single writer thread, so only one write is in flight at a time. This is
cheap to implement and it does not actually solve the problem. It makes writes
atomic, so you never get a half written file, but the sequence above has both
writes atomic already, and the update is still lost. Making it correct requires
the writer to check that the file has not changed since the agent read it and to
refuse the write if it has, which is optimistic concurrency control. Then you
need to decide what the agent does when refused, and the answer is that it must
re read and redo its work.

The second is to give each worker its own copy of the workspace. A git worktree
or a copied directory per agent, so there is no shared file to lose. Every agent
writes freely, nobody overwrites anybody, and the conflicts surface at the end as
a merge, which is a problem with forty years of tooling behind it. This is what
the serious harnesses do, and it is why agent tools have grown worktree support.
The cost is real. Copying a workspace is not free, a build directory per agent
multiplies disk and build time, and some jobs need to see each other's changes to
be correct at all.

This lesson does nothing about it.

`fanout.py` has no lock, no version check and no isolation. `tools.py` is byte
for byte what it was in lesson 20, which means `edit_file` will happily do what
you just watched it do. That is stated plainly because the alternative is a
chapter that shows you a fan out and lets you find this out on your own code.

The honest fix, and it is the one to actually use, is to **only parallelise jobs
that read**. Review four modules in parallel, search four directories in
parallel, summarise four documents in parallel, and collect four answers. Then
apply the changes one at a time, sequentially, from the parent, which is exactly
what lesson 20's `for call in calls` already does.

That rule costs you almost nothing in practice, because reading is where the
time goes. The four agents in section 1 spent forty seconds each, and nearly all
of it was searching and reading. The edits at the end are seconds. Parallelising
the slow safe part and serialising the fast dangerous part gets you the speedup
without the race, and it is a rule you can hold in your head, which a locking
scheme is not.

If you want the general version, the exercise is the second answer above. Give
each job its own copy of the workspace, run the fan out, and merge. Then find out
how you tell the parent which copy to believe.

## 9. Patterns worth knowing

Three shapes. The first is what this chapter built, the other two are the same
machinery arranged differently.

Fan out and gather splits work into independent jobs, runs them at once and
merges the results. `run_in_parallel` is exactly this. Use it when the jobs do not
need each other, which you check by asking whether job three would change if job
one had never run. Review four modules. Search four repositories. Summarise
twenty documents. It is the only pattern here that gives you a speedup, because
it is the only one where the work is genuinely independent.

An orchestrator that plans then delegates has one agent read the task and
decide what the jobs are, then hand them out. The difference from fan out is
that the job list is produced by a model rather than written by you, which
makes it adaptive and makes it a place where things go wrong. A planner that
emits eight jobs where three would do costs you eight agent runs, and a
planner that emits jobs which secretly depend on each other reintroduces the
race in section 8 with nobody having decided to. In this codebase the
orchestrator is the parent from lesson 20, emitting several `run_subagent`
calls in one turn, and the change is dispatching those calls through
`run_in_parallel` rather than the sequential `for call in calls`.

A reviewer that checks another agent's work is the last pattern. One agent
does the job, a second agent with a fresh context is given the result and
asked what is wrong with it. This is not a speedup and does not use
`fanout.py` at all. It is sequential by nature, since the reviewer needs the
thing being reviewed. What it buys is that the reviewer has not spent forty
turns convincing itself the approach was right, so it is far more likely to
notice that the tests were never run. The cost is one more full agent run per
job, and the risk is that a reviewer with no ability to check anything
mechanically will produce plausible approval, which is why the reviewer should
be given `run_shell` and asked for evidence rather than an opinion. Lesson 22
is what turns that from a hope into a measurement.

## 10. Running check.py

From inside the lesson folder.

```bash
cd lessons/21-multi-agent
python check.py
```

```text
OK three jobs ran at once and every event arrived
OK each job kept its own order even though the output was interleaved
OK one job failing did not take the batch with it, and the failure was reported
OK two jobs that each wait 0.3 seconds finished in 0.30, so they overlapped
```

Or every lesson at once against the built in mock server, which is what CI runs.

```bash
python ci/run_lessons.py
```

Note what is not in that output. There is no provider, no model and no network.
`check.py` never imports `agent.py`. The jobs are `steps`, a function that yields
three strings.

```python
def steps(label, count, pause=0.0):
    def produce():
        for index in range(count):
            if pause:
                time.sleep(pause)
            yield f"{label}-{index}"

    return produce
```

That is deliberate and it is the same argument lesson 14 made about
`fit_to_budget`. `run_in_parallel` does not know what an agent is. Its contract
is that you hand it callables returning iterators, so the honest way to test it
is with the simplest callable returning an iterator that exists. Putting a real
agent in this check would add a provider, a socket and a mock server to a test
about queue mechanics, and when it failed you would not know which of the four
things broke.

If the first line fails, events are being lost, and the place to look is the
termination condition in the main loop. If the second fails, something is
consuming the iterators outside the worker or events are being reordered on the
way to the queue. If the third fails, either the `except` is not catching or the
`finally` is not running, and if it hangs rather than failing, it is definitely
the `finally`. If the fourth fails and reports about six tenths of a second, the
jobs are running one after another, and the likely cause is calling `produce()`
on the main thread instead of inside `work`.

## 11. What you cannot do yet

You now have a harness that connects to tools it did not write, starts other
agents, and runs several of them at once. Stop and ask one question about all of
it.

Is any of it better?

Not faster. Section 7 measured faster and faster is proved. Better, meaning does
the agent produce more correct work at acceptable cost than it did four chapters
ago.

You cannot answer that. Nothing you have built can.

Consider what you have actually changed recently. Lesson 19 connected MCP
servers, which added tools and also added their schemas to every request, and
lesson 19 itself warned that more tools makes the model choose worse. Lesson 20
added subagents, which keep the parent's context clean and also mean the parent
is reasoning from an answer written by a model rather than from the tool results
themselves. This chapter gives you the machinery to run four of them at once,
which is faster and also means four agents forming four separate views of a
codebase they are all changing.

Every one of those is a trade. Not one of them has been measured. You have four
chapters of plausible improvements and no instrument, and the failure mode of
that situation is specific. You do not notice a regression. You accumulate
several, each individually defensible, and three weeks later the agent is worse
than it was and there is no way to find which change did it.

The parallel version makes this sharper than it was in lesson 18. A single agent
run that goes badly can at least be read in the session file from top to bottom.
Four agents produce four interleaved event streams and, as section 8 established,
a workspace whose final state depends on scheduling. Watching one run and forming
an impression was already weak evidence. Watching a run that would not reproduce
identically even with no changes at all is not evidence.

What you need is a fixed set of tasks with checkable outcomes, run the same way
every time, so that a change to a prompt or a model or a fan out width becomes an
experiment with a number at the end rather than a feeling. For the outcomes that
cannot be checked mechanically, because the answer is prose, you need a judge.
And once you have that, choosing between models stops being an opinion and
becomes the same experiment with one variable changed.

That is lesson 22.

On to lesson 22.
