"""Check that lesson 17 works.

Six things must be true. A failure that will pass later is retried until it
does. A failure caused by our own bad request is not retried at all, because
sending the same wrong thing again is just slower. When the server says when
to come back, we listen to it rather than to our own formula. The delay is
jittered so that clients do not all return at the same instant. A
cancellation stops real work rather than only the display. And a model that
has got stuck repeating itself is warned and then stopped.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson17-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import httpx  # noqa: E402
from cancel import Cancellation  # noqa: E402
from retry import delay_for, with_retries  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


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


def main():
    attempts = []

    def flaky():
        attempts.append(1)
        return post({"X-Mock-Fail": "500", "X-Mock-Fail-Times": "2"})

    body = with_retries(flaky, sleep=lambda seconds: None)
    if not body["choices"]:
        fail("the retried call did not eventually return a real answer")
    if len(attempts) != 3:
        fail(f"expected two failures and one success, saw {len(attempts)} attempts")
    print(f"OK a server error was retried until it worked, after {len(attempts)} attempts")

    bad_attempts = []

    def broken():
        bad_attempts.append(1)
        return post({"X-Mock-Fail": "400"})

    try:
        with_retries(broken, sleep=lambda seconds: None)
        fail("a bad request should have been raised, not swallowed")
    except httpx.HTTPStatusError:
        pass
    if len(bad_attempts) != 1:
        fail(f"a bad request was retried {len(bad_attempts)} times, it must not be retried at all")
    print("OK a bad request is not retried, because the same wrong request stays wrong")

    waited = []
    try:
        with_retries(lambda: post({"X-Mock-Fail": "429"}), attempts=2, sleep=waited.append)
    except httpx.HTTPStatusError:
        pass
    if waited != [2.0]:
        fail(f"the Retry-After header of 2 seconds was not obeyed. Waited {waited}")
    print("OK when the server says when to come back, we wait exactly that long")

    spread = {delay_for(3) for _ in range(20)}
    if len(spread) < 2:
        fail("the delay has no jitter, so every client would retry at the same instant")
    print(f"OK the delay is jittered across {len(spread)} different values")

    cancellation = Cancellation()
    cancellation.cancel()
    try:
        cancellation.raise_if_cancelled()
        fail("a cancelled token did not stop anything")
    except KeyboardInterrupt:
        pass
    print("OK a cancelled token stops work rather than only printing a message")

    from agent import run
    from permissions import Permissions

    class AlwaysTheSameCall:
        """A model that has got stuck, which is the case a turn limit misses."""

        def stream(self, messages, tools=None, on_text=None):
            return "", [
                {
                    "id": "c1",
                    "name": "read_file",
                    "arguments": {"path": "nowhere.txt"},
                    "error": "",
                }
            ], {}

    answer, _ = run(
        AlwaysTheSameCall(),
        "go",
        permissions=Permissions(auto_approve=True),
        max_turns=20,
    )
    if "Stopping" not in answer:
        fail(f"a stuck model was not stopped. Got {answer!r}")
    print("OK a model repeating one call is warned, then stopped, without burning every turn")


if __name__ == "__main__":
    main()
