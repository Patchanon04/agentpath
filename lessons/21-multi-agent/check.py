"""Check that lesson 21 works.

Four things must be true. Several jobs run at the same time and all of them
finish. The events of one job stay in order even though they arrive mixed in
with another job's. A job that fails does not take the batch with it. And the
work really does overlap rather than happening one after another, which is
the only reason to accept the complexity at all.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson21-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

from fanout import FanoutError, run_in_parallel  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def steps(label, count, pause=0.0):
    def produce():
        for index in range(count):
            if pause:
                time.sleep(pause)
            yield f"{label}-{index}"

    return produce


def main():
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
    print("OK one job failing did not take the batch with it, and the failure was reported")

    slow = [("x", steps("x", 1, pause=0.3)), ("y", steps("y", 1, pause=0.3))]
    started = time.monotonic()
    list(run_in_parallel(slow, workers=2))
    elapsed = time.monotonic() - started
    if elapsed > 0.55:
        fail(f"the jobs ran one after another, taking {elapsed:.2f} seconds")
    print(f"OK two jobs that each wait 0.3 seconds finished in {elapsed:.2f}, so they overlapped")


if __name__ == "__main__":
    main()
