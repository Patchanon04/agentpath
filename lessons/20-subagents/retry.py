"""Retrying the things that are safe to retry.

Three ideas matter here and each one is a mistake people make.

The provider knows better than we do. When a response carries Retry-After we
wait exactly that long. Our own doubling formula is the fallback for when the
server said nothing, not an opinion that overrides it.

Jitter is not decoration. Without it every client that failed at the same
moment retries at the same moment, which turns one bad second into a
sustained outage that the clients themselves are causing.

Not everything may be retried. Asking the model again is safe because it
changes nothing outside the conversation. Running a tool that sent an email
is not, which is why nothing in this module wraps a tool call.
"""
import random
import time

import httpx

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


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


def with_retries(call, attempts=4, sleep=time.sleep):
    """Run call, retrying only the failures that retrying can fix.

    A 400 means the request itself was wrong, so sending the same wrong
    request again produces the same wrong answer more slowly. Only statuses
    that mean try again later, and transport failures where nothing arrived
    at all, are worth a second attempt.
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
