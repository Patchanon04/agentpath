"""Check that lesson 08 works.

Three things must be true. A command runs and its output comes back. A
command the user refuses does not run, which we prove by checking that the
file it would have created does not exist. A command that hangs is reported
as a message rather than crashing the agent.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson08-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)
os.environ["AGENTPATH_AUTO_APPROVE"] = "1"

import tools  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    hello = tools.run("run_shell", {"command": f'"{sys.executable}" -c "print(\'hello\')"'})
    if "hello" not in hello:
        fail(f"the command output did not come back. Got {hello!r}")
    print("OK a command ran and its output came back")

    marker = workspace / "should-not-exist.txt"
    command = f"\"{sys.executable}\" -c \"open(r'{marker.as_posix()}', 'w').write('x')\""
    tools.confirm = lambda command: False
    refused = tools.run("run_shell", {"command": command})
    if "refused" not in refused:
        fail(f"a refused command did not report a refusal. Got {refused!r}")
    if marker.exists():
        fail("a refused command still ran, which is the bug this check exists to catch")
    print("OK a refused command did not run")

    tools.confirm = lambda command: True
    tools.SHELL_TIMEOUT = 1
    slow = tools.run("run_shell", {"command": f'"{sys.executable}" -c "import time; time.sleep(5)"'})
    if "timed out" not in slow:
        fail(f"a hanging command was not reported as a timeout. Got {slow!r}")
    print("OK a hanging command was reported as a timeout")


if __name__ == "__main__":
    main()
