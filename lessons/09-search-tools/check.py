"""Check that lesson 09 works.

Three things must be true. glob_files finds files by name. grep_files
reports the file name and the line number of every match. Directories such
as .venv are skipped, because searching a virtual environment returns
thousands of irrelevant hits and fills the context window with noise.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson09-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import tools  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    (workspace / "src").mkdir()
    (workspace / "src" / "main.py").write_text("def start():\n    return 1\n", encoding="utf-8")
    (workspace / "notes.md").write_text("start here\n", encoding="utf-8")
    (workspace / ".venv").mkdir()
    (workspace / ".venv" / "junk.py").write_text("def start():\n", encoding="utf-8")

    found = tools.run("glob_files", {"pattern": "**/*.py"})
    if "src/main.py" not in found:
        fail(f"glob_files did not find the source file. Got {found!r}")
    print("OK glob_files found the source file")

    if "junk.py" in found:
        fail("glob_files searched inside .venv, which it must skip")
    print("OK glob_files skipped the virtual environment")

    hits = tools.run("grep_files", {"pattern": "def start"})
    if "main.py" not in hits or ":1:" not in hits:
        fail(f"grep_files did not report the file and line number. Got {hits!r}")
    print("OK grep_files reported the file name and line number")

    limited = tools.run("grep_files", {"pattern": "start", "glob": "*.md"})
    if "notes.md" not in limited or "main.py" in limited:
        fail(f"the glob filter did not narrow the search. Got {limited!r}")
    print("OK the glob filter narrowed the search")


if __name__ == "__main__":
    main()
