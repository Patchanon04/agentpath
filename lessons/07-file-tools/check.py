"""Check that lesson 07 works.

This check proves four things. The agent can read a real file. It can edit a
real file and the change lands on disk. It cannot escape the workspace. It
cannot read a credential file, and the secret inside never appears in the
result.

The workspace is set before tools is imported, because tools reads
AGENTPATH_WORKSPACE once when the module loads.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson07-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import tools  # noqa: E402
from agent import run  # noqa: E402
from providers import OpenAICompatProvider  # noqa: E402

READ_AND_EDIT = (
    "Fix the bug in calc.py. "
    '[[tool:read_file:{"path": "calc.py"}]]'
    '[[tool:edit_file:{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]]'
)


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    (workspace / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (workspace / ".env").write_text("API_KEY=supersecretvalue\n", encoding="utf-8")

    if "return a - b" not in tools.read_file("calc.py"):
        fail("read_file did not return the file contents")
    print("OK read_file returned the real file")

    provider = OpenAICompatProvider(
        os.environ["AGENTPATH_BASE_URL"],
        os.environ.get("AGENTPATH_API_KEY", ""),
        os.environ["AGENTPATH_MODEL"],
    )
    run(provider, READ_AND_EDIT)
    if "return a + b" not in (workspace / "calc.py").read_text(encoding="utf-8"):
        fail("the agent did not edit the file on disk")
    print("OK the agent edited a real file on disk")

    escape = tools.run("read_file", {"path": "../../secrets.txt"})
    if "outside the workspace" not in escape:
        fail(f"an escape attempt was not refused. Got {escape!r}")
    print("OK a path outside the workspace was refused")

    secret = tools.run("read_file", {"path": ".env"})
    if "refuses to touch" not in secret or "supersecretvalue" in secret:
        fail(f"the credential file was not protected. Got {secret!r}")
    print("OK reading .env was refused and the secret did not leak")


if __name__ == "__main__":
    main()
