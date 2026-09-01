"""Running several agents at once and merging what they say.

Threads rather than async, for the same reason the rest of the project is
synchronous. An agent run spends nearly all of its life waiting on a socket,
which is the case threads handle well, and async would put a second mental
model in front of a reader who came here to learn about agents.

The hard part is not starting the work. It is that several agents talking at
once produce interleaved output, and text with no label is unreadable. Every
event therefore travels with the name of the job that produced it, and the
caller decides how to present that.
"""
import queue
import threading

DONE = object()


def run_in_parallel(jobs, workers=4):
    """Run jobs concurrently and yield (label, event) as results arrive.

    jobs is a list of (label, callable) where the callable returns an
    iterator of events. Order across jobs is not defined and cannot be,
    because that is what running at the same time means. Order within one
    job is preserved, which is the part that actually matters.

    A job that raises does not stop the others. It yields one final event of
    its own describing the failure, because a batch where one item silently
    vanished is worse than one that reports a problem.
    """
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
        threading.Thread(target=work, daemon=True)
        for _ in range(max(1, min(workers, len(jobs))))
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


class FanoutError:
    """One job failed. Reported as an event so the caller sees it in order."""

    def __init__(self, label, error):
        self.label = label
        self.error = error

    def __repr__(self):
        return f"FanoutError({self.label!r}, {self.error!r})"
