import time

import pytest

from agentpath.fanout import FanoutError, run_in_parallel


def steps(label, count, pause=0.0):
    def produce():
        for index in range(count):
            if pause:
                time.sleep(pause)
            yield f"{label}-{index}"

    return produce


def test_no_jobs_produces_nothing():
    assert list(run_in_parallel([])) == []


def test_every_event_from_every_job_arrives():
    jobs = [("a", steps("a", 3)), ("b", steps("b", 3)), ("c", steps("c", 3))]
    seen = list(run_in_parallel(jobs, workers=3))
    assert len(seen) == 9
    for label in ["a", "b", "c"]:
        assert [event for name, event in seen if name == label] == [
            f"{label}-0",
            f"{label}-1",
            f"{label}-2",
        ]


def test_order_within_one_job_is_preserved_even_when_jobs_interleave():
    """Order across jobs is undefined and cannot be. Order within one is the promise."""
    jobs = [("slow", steps("slow", 4, pause=0.01)), ("fast", steps("fast", 4))]
    seen = list(run_in_parallel(jobs, workers=2))
    slow = [event for label, event in seen if label == "slow"]
    assert slow == ["slow-0", "slow-1", "slow-2", "slow-3"]


def test_more_jobs_than_workers_still_all_finish():
    jobs = [(str(index), steps(str(index), 2)) for index in range(10)]
    seen = list(run_in_parallel(jobs, workers=2))
    assert len(seen) == 20
    assert {label for label, _ in seen} == {str(index) for index in range(10)}


def test_one_failing_job_does_not_stop_the_others():
    def explode():
        yield "before"
        raise RuntimeError("this job broke")

    jobs = [("good", steps("good", 2)), ("bad", explode)]
    seen = list(run_in_parallel(jobs, workers=2))
    good = [event for label, event in seen if label == "good"]
    bad = [event for label, event in seen if label == "bad"]
    assert good == ["good-0", "good-1"]
    assert bad[0] == "before"
    assert isinstance(bad[-1], FanoutError)
    assert "this job broke" in repr(bad[-1])


def test_work_really_happens_at_the_same_time():
    """Two jobs that each sleep should not take twice as long as one."""
    jobs = [("a", steps("a", 1, pause=0.3)), ("b", steps("b", 1, pause=0.3))]
    started = time.monotonic()
    list(run_in_parallel(jobs, workers=2))
    elapsed = time.monotonic() - started
    assert elapsed < 0.55, f"the jobs appear to have run one after the other, took {elapsed:.2f}s"


@pytest.mark.parametrize("workers", [1, 2, 8])
def test_the_result_is_the_same_whatever_the_worker_count(workers):
    jobs = [(str(index), steps(str(index), 2)) for index in range(4)]
    seen = list(run_in_parallel(jobs, workers=workers))
    assert len(seen) == 8

def test_a_worker_count_of_zero_does_not_hang():
    """Zero threads and a queue nobody fills is a wait that never ends."""
    assert len(list(run_in_parallel([("a", steps("a", 2))], workers=0))) == 2


def test_a_malformed_job_does_not_hang_the_batch():
    """The worker died before posting its sentinel, and the main loop counts
    sentinels, so it waited for one that was never coming."""
    events = list(run_in_parallel([("broken",), ("good", steps("good", 1))], workers=1))
    labels = [label for label, _ in events]
    assert "good" in labels
    assert any(isinstance(event, FanoutError) for _, event in events)
