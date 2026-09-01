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
