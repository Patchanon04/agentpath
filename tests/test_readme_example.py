"""The example in the README has to run, because somebody will paste it.

It is the first code a person who installed the package sees, and it is the
one block in the project that no chapter check and no lesson check covers.
Every other kind of drift in this repository has already happened at least
once, so an example that quietly stops working is a matter of time rather
than of luck.

The block is extracted from the README rather than copied here. A copy
would be a second version to keep in step, which is the argument lesson 09
makes about rules written twice.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)

READMES = [ROOT / "README.md", ROOT / "README.th.md"]


def library_example(readme):
    """The one block that imports the package and drives an agent."""
    for block in BLOCK.findall(readme.read_text(encoding="utf-8")):
        if "from agentpath import" in block and "agent.run(" in block:
            return block
    return None


def test_the_readme_has_an_example_at_all():
    """If the example is deleted, this file must fail rather than pass empty."""
    assert library_example(READMES[0]), (
        "the README no longer shows how to use the package as a library, and "
        "the test that proves the example works is now proving nothing"
    )


@pytest.mark.parametrize("readme", READMES, ids=lambda p: p.name)
def test_the_readme_example_runs(readme, mock_url, tmp_path):
    """Run it exactly as printed, in a fresh process, against the mock server.

    A fresh process matters. Running it here would let it import names the
    test file already imported, and the thing most likely to break is an
    import, because the front door in __init__ is a list somebody has to
    remember to update.
    """
    example = library_example(readme)
    assert example, f"{readme.name} has no library example to run"

    script = tmp_path / "example.py"
    script.write_text(example, encoding="utf-8")
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")

    environment = dict(os.environ)
    environment["AGENTPATH_BASE_URL"] = mock_url
    environment["AGENTPATH_MODEL"] = "mock"
    environment["AGENTPATH_WORKSPACE"] = str(tmp_path)

    finished = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(tmp_path),
        env=environment,
    )
    assert finished.returncode == 0, finished.stderr[-800:]
    assert finished.stdout.strip(), "the example ran and printed nothing"


def test_both_readmes_show_the_same_example():
    """The translation is a translation, so its code is untouched."""
    english, thai = (library_example(path) for path in READMES)
    assert english == thai, "the Thai README shows a different example"
