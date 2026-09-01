"""Check that lesson 16 works.

The point of this chapter is a decision rather than a technique, so the
check demonstrates both sides of it. Retrieval finds the passage that
answers a question asked in ordinary words. And grep beats retrieval when
you already know the exact word you are looking for, which is most of the
time when the corpus is code.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson16-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import tools  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    (workspace / "refunds.md").write_text(
        "# Refunds\n\nCustomers may request a refund within thirty days of purchase.\n\n"
        "Refunds are paid back to the original card.\n",
        encoding="utf-8",
    )
    (workspace / "shipping.md").write_text(
        "# Shipping\n\nOrders are dispatched within two working days.\n\n"
        "Delivery takes three to five days.\n",
        encoding="utf-8",
    )
    (workspace / "team.md").write_text(
        "# The team\n\nThe team works remotely across three time zones.\n",
        encoding="utf-8",
    )
    (workspace / "billing.py").write_text(
        "def issue_refund(order_id):\n    return True\n", encoding="utf-8"
    )

    answer = tools.run("search_notes", {"question": "how long to ask for a refund"})
    if not answer.startswith("refunds.md"):
        fail(f"retrieval did not find the right document. Got {answer[:80]!r}")
    print("OK a question in ordinary words found the right passage")

    if ":" not in answer.splitlines()[0]:
        fail("a passage came back with no source, so the agent cannot go and read more")
    print("OK every passage says which file and line it came from")

    nothing = tools.run("search_notes", {"question": "quantum entanglement"})
    if "nothing in the documents" not in nothing:
        fail("a question about nothing in the corpus did not say so")
    print("OK a question with no matching words says so instead of guessing")

    missed = tools.run("search_notes", {"question": "dispatch"})
    if "nothing in the documents" not in missed:
        fail("this check is wrong, dispatch should not match dispatched")
    print("OK word matching does not understand word endings, which is the honest limit")

    exact = tools.run("grep_files", {"pattern": "issue_refund", "glob": "*.py"})
    if "billing.py" not in exact:
        fail("grep did not find an exact name, which is what it is for")
    print("OK when you know the exact name, grep answers directly and costs nothing to build")


if __name__ == "__main__":
    main()
