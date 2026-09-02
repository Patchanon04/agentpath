"""The chapters have to be as safe as the library, and nothing checked that.

Three times now a fix landed in src/agentpath and never reached the
seventeen copies of the same code in lessons/. Twice it was a security fix, so the
course was teaching people to write the vulnerable version while the book
told them it was fixed. Nothing caught it because the lesson checks prove a
tool works, never that it refuses.

So this file runs the lesson code and asks it the questions the library gets
asked. Each lesson is exercised in its own process, because every lesson
folder has a module called tools and they cannot all be imported into one
interpreter.

It is slower than the rest of the suite. That is the price of the chapters
and the library being able to drift apart, and it is worth paying.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

LESSONS = Path(__file__).resolve().parents[1] / "lessons"
SECRET = "SUPERSECRETVALUE"
OUTSIDE = "OUTSIDEVALUE"

PROBE = '''
import json, os, sys, time
sys.path.insert(0, LESSON)
os.environ["AGENTPATH_WORKSPACE"] = WORKSPACE
os.environ["AGENTPATH_AUTO_APPROVE"] = "1"
os.chdir(WORKSPACE)

import tools

answers = {}


def ask(name, arguments):
    try:
        return tools.run(name, arguments)
    except Exception as error:
        return f"RAISED {type(error).__name__}: {error}"


answers["reads_a_real_file"] = ask("read_file", {"path": "ok.py"})
answers["escape_by_path"] = ask("read_file", {"path": "../outside/secret.txt"})
answers["reads_env"] = ask("read_file", {"path": ".env"})

if "write_file" in tools.FUNCTIONS:
    answers["writes_env"] = ask("write_file", {"path": ".env", "content": "REPLACED"})
    answers["env_still_says"] = open(
        os.path.join(WORKSPACE, ".env"), encoding="utf-8"
    ).read()

if "grep_files" in tools.FUNCTIONS:
    answers["grep_env"] = ask("grep_files", {"pattern": "API_KEY"})
    answers["grep_through_link"] = ask("grep_files", {"pattern": "value"})
    answers["glob_everything"] = ask("glob_files", {"pattern": "**/*"})
    answers["grep_ordinary"] = ask("grep_files", {"pattern": "def start"})
    started = time.monotonic()
    answers["grep_catastrophic"] = ask("grep_files", {"pattern": "(a|a)+$"})
    answers["catastrophic_seconds"] = time.monotonic() - started
    answers["ran_workspace_code"] = os.path.exists(os.path.join(WORKSPACE, "EXECUTED.txt"))

print("---BEGIN---")
print(json.dumps(answers))
'''


def lessons_with_tools():
    """Every lesson folder that has a tools.py at all."""
    return sorted(p.parent for p in LESSONS.glob("*/tools.py"))


def lessons_with(function):
    """Lessons whose tools.py defines a given function.

    Lessons 03 to 06 have only the toy tools from the tool calling chapter,
    so asking them to refuse a path they cannot take would fail for the
    wrong reason. Selecting by what the file actually defines means a lesson
    that gains file tools later is picked up without anybody editing a list.
    """
    return [
        lesson
        for lesson in lessons_with_tools()
        if f"def {function}(" in (lesson / "tools.py").read_text(encoding="utf-8")
    ]


def lesson_id(path):
    """pytest calls this once per value, so it takes one path not a list."""
    return path.name


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    """One workspace, shared, holding every trap at once."""
    root = tmp_path_factory.mktemp("parity") / "workspace"
    root.mkdir()
    outside = root.parent / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(f"value={OUTSIDE}\n", encoding="utf-8")
    (outside / "readable.md").write_text(f"value is {OUTSIDE}\n", encoding="utf-8")
    (root / ".env").write_text(f"API_KEY={SECRET}\n", encoding="utf-8")
    (root / "ok.py").write_text("def start():\n    return 1\n", encoding="utf-8")
    (root / "long.txt").write_text(("a" * 40 + "!\n") * 20, encoding="utf-8")

    proof = root / "EXECUTED.txt"
    for shadowed in ["json", "fnmatch", "types"]:
        (root / f"{shadowed}.py").write_text(
            f'open(r"{proof}", "w").write("ran")\n', encoding="utf-8"
        )

    link = root / "vendor"
    if sys.platform == "win32":
        subprocess.run(f'mklink /J "{link}" "{outside}"', shell=True, capture_output=True)
    else:
        link.symlink_to(outside, target_is_directory=True)
    return root


@pytest.fixture(scope="module")
def answers(workspace, tmp_path_factory):
    """Run every lesson once and keep what each one said."""
    collected = {}
    scripts = tmp_path_factory.mktemp("probes")
    for lesson in lessons_with_tools():
        script = scripts / f"probe_{lesson.name.replace('-', '_')}.py"
        script.write_text(
            f"LESSON = {str(lesson)!r}\nWORKSPACE = {str(workspace)!r}\n" + PROBE,
            encoding="utf-8",
        )
        (workspace / "EXECUTED.txt").unlink(missing_ok=True)
        finished = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(scripts),
        )
        if "---BEGIN---" not in finished.stdout:
            collected[lesson.name] = {"failed_to_run": finished.stderr[-400:]}
            continue
        collected[lesson.name] = json.loads(finished.stdout.split("---BEGIN---", 1)[1])
    return collected


@pytest.mark.parametrize("lesson", lessons_with_tools(), ids=lesson_id)
def test_the_lesson_code_runs_at_all(answers, lesson):
    said = answers[lesson.name]
    assert "failed_to_run" not in said, said.get("failed_to_run")


@pytest.mark.parametrize("lesson", lessons_with("read_file"), ids=lesson_id)
def test_the_lesson_still_does_ordinary_work(answers, lesson):
    """Checked first, because a refusal that refuses everything is not safety."""
    said = answers[lesson.name]
    assert "def start" in said["reads_a_real_file"], said["reads_a_real_file"][:120]


@pytest.mark.parametrize("lesson", lessons_with("read_file"), ids=lesson_id)
def test_the_lesson_refuses_a_path_outside_the_workspace(answers, lesson):
    said = answers[lesson.name]
    assert OUTSIDE not in said["escape_by_path"]
    assert "outside the workspace" in said["escape_by_path"]


@pytest.mark.parametrize("lesson", lessons_with("read_file"), ids=lesson_id)
def test_the_lesson_refuses_to_read_a_credential_file(answers, lesson):
    said = answers[lesson.name]
    assert SECRET not in said["reads_env"]


@pytest.mark.parametrize("lesson", lessons_with("write_file"), ids=lesson_id)
def test_the_lesson_refuses_to_write_over_a_credential_file(answers, lesson):
    """The library grew this test in the same round. The lessons need it too.

    A lesson that can be told to overwrite .env teaches a tool that can
    destroy the reader's own setup on the first run.
    """
    said = answers[lesson.name]
    assert "Error" in said["writes_env"], said["writes_env"][:120]
    assert SECRET in said["env_still_says"], "the lesson overwrote a credential file"


@pytest.mark.parametrize(
    "lesson", [p for p in lessons_with_tools() if (p / "grep_worker.py").exists()], ids=lesson_id
)
def test_the_lesson_search_honours_the_same_rules_as_the_library(answers, lesson):
    """The bug that shipped twice, asked of the chapters rather than the library."""
    said = answers[lesson.name]
    assert SECRET not in said["grep_env"], "search handed back a credential file"
    assert OUTSIDE not in said["grep_through_link"], "search read through a link"
    assert OUTSIDE not in said["glob_everything"]
    assert "ok.py:1:" in said["grep_ordinary"], "search stopped doing ordinary work"


@pytest.mark.parametrize(
    "lesson", [p for p in lessons_with_tools() if (p / "grep_worker.py").exists()], ids=lesson_id
)
def test_the_lesson_search_gives_up_on_a_runaway_pattern(answers, lesson):
    said = answers[lesson.name]
    assert said["catastrophic_seconds"] < 20, (
        f"the search ran for {said['catastrophic_seconds']:.1f} seconds"
    )
    assert "Error" in said["grep_catastrophic"]


@pytest.mark.parametrize(
    "lesson", [p for p in lessons_with_tools() if (p / "grep_worker.py").exists()], ids=lesson_id
)
def test_the_lesson_search_does_not_run_code_from_the_workspace(answers, lesson):
    said = answers[lesson.name]
    assert not said["ran_workspace_code"], "the lesson worker executed a workspace file"


def test_every_lesson_that_searches_ships_the_worker_it_needs():
    """A folder is supposed to be complete on its own."""
    missing = [
        lesson.name
        for lesson in lessons_with_tools()
        if "grep_worker" in (lesson / "tools.py").read_text(encoding="utf-8")
        and not (lesson / "grep_worker.py").exists()
    ]
    assert not missing, f"these lessons call a worker they do not ship {missing}"


def test_the_search_rules_are_written_once_per_lesson():
    """The worker used to carry its own copy of the rules, and one went stale.

    A rule in two places agrees until somebody edits one of them, which is
    the argument lesson 09 makes in its own prose about gates.
    """
    duplicated = []
    for lesson in lessons_with_tools():
        worker = lesson / "grep_worker.py"
        if not worker.exists():
            continue
        text = worker.read_text(encoding="utf-8")
        for rule in ["SECRET_NAMES =", "SKIP_DIRECTORIES =", "def looks_like_a_secret"]:
            if rule in text:
                duplicated.append(f"{lesson.name} redefines {rule.rstrip(' =')}")
    assert not duplicated, duplicated
