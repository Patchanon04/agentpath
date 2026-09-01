import httpx
import pytest

from agentpath.retry import delay_for, with_retries


class FakeResponse:
    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}


def status_error(code, headers=None):
    return httpx.HTTPStatusError(
        "boom", request=httpx.Request("POST", "http://x"), response=FakeResponse(code, headers)
    )


def test_a_call_that_works_is_not_retried():
    calls = []
    assert with_retries(lambda: calls.append(1) or "done", sleep=lambda s: None) == "done"
    assert len(calls) == 1


def test_a_server_error_is_retried_until_it_works():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise status_error(500)
        return "recovered"

    assert with_retries(flaky, sleep=lambda s: None) == "recovered"
    assert len(attempts) == 3


def test_a_bad_request_is_not_retried():
    """Sending the same wrong request again produces the same wrong answer."""
    attempts = []

    def broken():
        attempts.append(1)
        raise status_error(400)

    with pytest.raises(httpx.HTTPStatusError):
        with_retries(broken, sleep=lambda s: None)
    assert len(attempts) == 1


def test_the_retry_after_header_wins_over_our_own_formula():
    """The server is telling us when it will be ready. Guessing earlier is rude and useless."""
    assert delay_for(1, FakeResponse(429, {"Retry-After": "7"})) == 7.0
    assert delay_for(5, FakeResponse(429, {"Retry-After": "7"})) == 7.0


def test_a_nonsense_retry_after_falls_back_to_the_formula():
    assert 0 < delay_for(1, FakeResponse(429, {"Retry-After": "soon"})) <= 1.0


def test_the_delay_grows_with_each_attempt():
    early = [delay_for(1) for _ in range(30)]
    late = [delay_for(4) for _ in range(30)]
    assert max(early) < min(late)


def test_the_delay_has_jitter():
    """Without jitter every client retries at the same instant and keeps the outage going."""
    assert len({delay_for(3) for _ in range(20)}) > 1


def test_the_delay_is_capped():
    assert delay_for(20) <= 30.0


def test_a_transport_failure_is_retried():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 2:
            raise httpx.ConnectError("no route")
        return "recovered"

    assert with_retries(flaky, sleep=lambda s: None) == "recovered"


def test_giving_up_raises_the_last_error():
    with pytest.raises(httpx.HTTPStatusError):
        with_retries(lambda: (_ for _ in ()).throw(status_error(503)), sleep=lambda s: None)
