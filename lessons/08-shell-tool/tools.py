"""Tools that touch real files.

Two new ideas arrive in this file. The first is that every path the model
sends us goes through one gate called resolve_inside, so the rules about
what may be touched live in one place instead of being repeated in four
functions. The second is that everything a tool returns is sent to the model
provider on this request and on every later request in the conversation,
which is why we truncate output and why we refuse to read credential files.
"""
import os
from pathlib import Path

MAX_OUTPUT = 4000
SKIP_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", ".ruff_cache"}
SECRET_NAMES = {".env", "id_rsa", "id_ed25519", ".npmrc", ".netrc", "credentials"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}

WORKSPACE = Path(os.environ.get("AGENTPATH_WORKSPACE", ".")).resolve()


class WorkspaceError(Exception):
    """Raised when a tool asks for a path it is not allowed to have."""


def looks_like_a_secret(name):
    lowered = name.lower()
    if lowered in SECRET_NAMES or lowered.startswith(".env."):
        return True
    return Path(lowered).suffix in SECRET_SUFFIXES


def resolve_inside(path):
    """Turn a path from the model into a real path, or refuse it.

    Two separate refusals happen here. The first stops the agent from
    reaching outside its workspace at all, which covers both parent
    directory escapes such as ../../etc/passwd and absolute paths. The
    second stops it from reading credential files that happen to live inside
    the workspace, because once a key is in the conversation it is sent to
    the model provider on every later call and you cannot take it back.
    """
    candidate = (WORKSPACE / Path(path)).resolve()
    if candidate != WORKSPACE and not candidate.is_relative_to(WORKSPACE):
        raise WorkspaceError(f"{path} is outside the workspace")
    if looks_like_a_secret(candidate.name):
        raise WorkspaceError(
            f"this tool refuses to read {candidate.name} because credential files "
            "must not enter the conversation"
        )
    return candidate


def truncate(text, limit=MAX_OUTPUT):
    """Keep tool output small enough that it does not eat the context window."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[truncated, {len(text) - limit} more characters]"


def read_file(path):
    target = resolve_inside(path)
    if not target.is_file():
        return f"Error: {path} does not exist"
    return truncate(target.read_text(encoding="utf-8", errors="replace"))


def write_file(path, content):
    target = resolve_inside(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {path}"


def edit_file(path, old, new):
    """Replace one exact piece of text, but only when the match is unique.

    A replace that hits three places when the model meant one is a silent
    corruption. Refusing an ambiguous edit and asking for more surrounding
    context turns that disaster into a message the model can act on.
    """
    target = resolve_inside(path)
    if not target.is_file():
        return f"Error: {path} does not exist"
    text = target.read_text(encoding="utf-8")
    found = text.count(old)
    if found == 0:
        return (
            f"Error: the text to replace was not found in {path}. "
            "Read the file again and copy the exact text including whitespace."
        )
    if found > 1:
        return (
            f"Error: the text to replace appears {found} times in {path}. "
            "Include more surrounding lines so the match is unique."
        )
    target.write_text(text.replace(old, new), encoding="utf-8")
    return f"Edited {path}"


def list_files(path="."):
    target = resolve_inside(path)
    if not target.is_dir():
        return f"Error: {path} is not a directory"
    names = []
    for entry in sorted(target.iterdir()):
        if entry.name in SKIP_DIRECTORIES:
            continue
        names.append(entry.name + "/" if entry.is_dir() else entry.name)
    return truncate("\n".join(names) or "(empty directory)")


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write a whole file, creating it if needed. Use edit_file instead when "
                "you only want to change part of an existing file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"},
                    "content": {"type": "string", "description": "The complete new contents"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace one exact piece of text in a file. The old text must appear "
                "exactly once, so include enough surrounding lines to make it unique."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"},
                    "old": {"type": "string", "description": "The exact text to replace"},
                    "new": {"type": "string", "description": "The text to put in its place"},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List the files and directories in one directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory relative to the workspace",
                    }
                },
                "required": [],
            },
        },
    },
]

FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
}


def run(name, arguments):
    """Run one tool by name and return its result as a string."""
    function = FUNCTIONS.get(name)
    if function is None:
        return f"Error: unknown tool {name}"
    try:
        return str(function(**arguments))
    except WorkspaceError as error:
        return f"Error: {error}"
    except Exception as error:
        return f"Error: {type(error).__name__}: {error}"


# Lesson 08 adds the shell tool. Everything above is unchanged from lesson 07.

import signal
import subprocess  # noqa: E402

SHELL_TIMEOUT = 60


def confirm(command):
    """Ask the user before running anything.

    This one function is the entire safety story of lesson 08. A model can be
    talked into running something destructive by text it read out of a file,
    so the last gate before anything runs is a person.

    AGENTPATH_AUTO_APPROVE exists because an automated run has nobody at the
    keyboard. Without it every test and every continuous integration job
    would hang forever waiting for an answer that never arrives. It is not a
    hole in the safety story, it is the switch that says nobody is watching
    and you already decided that is fine.
    """
    if os.environ.get("AGENTPATH_AUTO_APPROVE") == "1":
        return True
    print(f"\nThe agent wants to run this command.\n\n    {command}\n")
    try:
        return input("Run it? [y/N] ").strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def _new_process_group():
    """Start the command in its own group so the whole tree can be killed.

    Without this there is nothing to aim at. On Unix the shell and its
    children share our group, so signalling the group would signal us too.
    On Windows a new process group is what lets taskkill find the
    descendants of the shell rather than only the shell.
    """
    if os.name == "posix":
        return {"start_new_session": True}
    return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}


def _kill_tree(process):
    """Kill the command and everything it started."""
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        else:
            killed = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                timeout=10,
            )
            if killed.returncode != 0:
                raise OSError(f"taskkill exited {killed.returncode}")
    except Exception:
        # Last resort. Killing only the shell beats killing nothing.
        try:
            process.kill()
        except Exception:
            pass


def _output_encodings():
    """The encodings to try on command output, in order.

    Assuming utf-8 is wrong on Windows. A command that writes utf-8, which
    most modern tools do, and a command that writes the old console codepage,
    which most of the ones that ship with the system do, both turn up on the
    same machine. Decoding the second as the first turns every accented or
    non Latin character into a replacement mark, and errors equals replace
    means it happens without a word.

    utf-8 goes first because it fails loudly on the wrong input. A single
    byte encoding never fails, so trying one of those first would decode
    utf-8 text into nonsense and never complain.
    """
    encodings = ["utf-8"]
    if os.name == "nt":
        import ctypes

        for codepage in (
            ctypes.windll.kernel32.GetOEMCP(),
            ctypes.windll.kernel32.GetACP(),
        ):
            name = f"cp{codepage}"
            if name not in encodings:
                encodings.append(name)
    return encodings


def decode_output(raw):
    """Turn the bytes a command produced into text."""
    for encoding in _output_encodings():
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


_CONSOLE_READY = False


def _use_utf8_console():
    """Put this process's console into utf-8, once.

    The chcp inside the command is not enough on its own. A shell builtin
    such as dir reads the codepage when the shell starts, which happens
    before the chcp in the same command line runs, so the first command of a
    session still lost non ASCII names while every later one was fine. That
    is a maddening thing to debug and the fix is to set it here instead,
    before any shell exists.

    This does change the codepage of the terminal the person is sitting in.
    It is a display setting, it is what any modern tool wants anyway, and the
    alternative is output that is quietly wrong.
    """
    global _CONSOLE_READY
    if _CONSOLE_READY or os.name != "nt":
        return
    _CONSOLE_READY = True
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        # No console attached, or not permitted. The chcp in the command is
        # the fallback and still helps every program the shell launches.
        pass


def as_utf8_console(command):
    """Ask the Windows shell to speak utf-8 before running the command.

    Without this the shell does the damage before we ever see the bytes.
    Listing a directory that holds a Thai file name on a console set to the
    old codepage prints question marks, because that codepage cannot write
    those characters at all. Decoding cannot recover what was never encoded.

    What this does not fix. When no console can be set, which happens when
    the agent runs with none attached, the shell reads the command line
    before the chcp takes effect and non ASCII characters inside the command
    itself are flattened. With a console it works. File names and command
    output are fine either way, which covers the cases that come up.

    The prefix is a fixed string the model cannot influence, and it changes
    nothing except the encoding. It is worth knowing that it makes the
    command that runs differ by these few characters from the one the person
    approved, which is why it is written out here rather than hidden.
    """
    if os.name != "nt":
        return command
    _use_utf8_console()
    return f"chcp 65001 >nul & {command}"


def run_shell(command):
    if not confirm(command):
        return "The user refused to run this command. Do not try to run it again."
    process = subprocess.Popen(
        as_utf8_console(command),
        shell=True,
        cwd=WORKSPACE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **_new_process_group(),
    )
    try:
        raw_out, raw_err = process.communicate(timeout=SHELL_TIMEOUT)
    except subprocess.TimeoutExpired:
        # shell=True means the thing we started is a shell and the slow
        # command is its child. Killing only the shell leaves the child
        # running and still holding the pipes, so a call meant to give up
        # after the timeout waits for the whole run anyway.
        _kill_tree(process)
        try:
            raw_out, raw_err = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            raw_out, raw_err = b"", b""
        partial = truncate(decode_output(raw_out) + decode_output(raw_err), 500)
        note = f"Error: the command timed out after {SHELL_TIMEOUT} seconds and was killed"
        return f"{note}\n{partial}" if partial.strip() else note

    stdout, stderr = decode_output(raw_out), decode_output(raw_err)
    parts = []
    if stdout:
        parts.append(stdout)
    if stderr:
        parts.append(stderr)
    if process.returncode != 0:
        parts.append(f"[exit code {process.returncode}]")
    return truncate("\n".join(parts) or "[no output]")


SCHEMAS.append(
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Run a shell command in the workspace directory and return its output. "
                "The user is asked to approve the command before it runs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command line to run"}
                },
                "required": ["command"],
            },
        },
    }
)

FUNCTIONS["run_shell"] = run_shell
