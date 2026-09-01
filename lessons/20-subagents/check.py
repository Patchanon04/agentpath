"""Check that lesson 20 works.

Five things must be true. A subagent is an ordinary tool as far as the
parent is concerned. It does real work that reaches the disk. It holds a
conversation of its own. None of that conversation lands in the parent,
which is the reason to use one at all. And a child that blows up leaves the
parent standing.

The sixth thing this file demonstrates is not a feature. It is the trap that
comes with the isolation, which is that the parent keeps believing whatever
it read before the child changed it.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson20-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import tools  # noqa: E402
from agent import run  # noqa: E402
from permissions import Permissions  # noqa: E402
from providers import OpenAICompatProvider  # noqa: E402
from subagent import run_subagent_factory  # noqa: E402

WRITE = 'Write it. [[tool:write_file:{"path": "made-by-child.txt", "content": "hello"}]]'


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def provider():
    return OpenAICompatProvider(
        os.environ["AGENTPATH_BASE_URL"],
        os.environ.get("AGENTPATH_API_KEY", ""),
        os.environ["AGENTPATH_MODEL"],
    )


def main():
    children = []

    def build_child():
        def child(task):
            answer, messages = run(
                provider(), task, permissions=Permissions(auto_approve=True)
            )
            children.append(messages)
            return answer, messages

        return child

    run_subagent, schema = run_subagent_factory(build_child)
    tools.SCHEMAS.append(schema)
    tools.FUNCTIONS["run_subagent"] = run_subagent

    if schema["function"]["name"] != "run_subagent":
        fail("the subagent did not turn into an ordinary tool")
    print("OK a subagent is an ordinary tool as far as the parent is concerned")

    answer = tools.run("run_subagent", {"task": WRITE})
    if not (workspace / "made-by-child.txt").exists():
        fail(f"the child did no real work. It said {answer!r}")
    print("OK the child did real work that reached the disk")

    if not children or len(children[0]) < 4:
        fail(f"the child conversation looks wrong. Got {children!r}")
    print(f"OK the child had a {len(children[0])} message conversation of its own")

    parent_answer, parent_messages = run(
        provider(), "Say hello.", permissions=Permissions(auto_approve=True)
    )
    if any("made-by-child" in (m.get("content") or "") for m in parent_messages):
        fail("the child conversation leaked into the parent")
    print(f"OK none of it landed in the parent, which kept {len(parent_messages)} messages")

    def build_broken():
        def child(task):
            raise RuntimeError("the child could not start")

        return child

    broken_tool, _ = run_subagent_factory(build_broken)
    result = broken_tool("anything")
    if not result.startswith("Error") or "could not start" not in result:
        fail(f"a failing child was not reported safely. Got {result!r}")
    print("OK a child that blew up left the parent standing")

    shared = workspace / "shared.txt"
    shared.write_text("original", encoding="utf-8")
    parent_saw = tools.run("read_file", {"path": "shared.txt"})
    tools.run(
        "run_subagent",
        {"task": 'Rewrite. [[tool:write_file:{"path": "shared.txt", "content": "changed"}]]'},
    )
    now = shared.read_text(encoding="utf-8")
    if parent_saw == now:
        fail("this demonstration is broken, the file should have changed")
    print(
        f"OK the trap is real, the parent still believes {parent_saw!r} "
        f"while the file now says {now!r}"
    )


if __name__ == "__main__":
    main()
