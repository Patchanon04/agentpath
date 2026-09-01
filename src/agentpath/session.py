"""Saving a conversation so you can come back to it.

The format is one JSON object per line, which is called JSONL. Two things
make it the right choice here. Each message is written the moment it
happens rather than at the end, so a crash loses nothing that already
finished. And you can open the file and read it, which matters more than it
sounds, because the session file is the first place to look when you want
to know why the agent did something.

This version supports one writer. Two processes appending to the same
session will interleave their lines and corrupt it. Real harnesses take a
lock before writing and release it after. That is left out here because the
locking is not the lesson, but the limit is real and you should know it.
"""
import json
import os
from dataclasses import asdict
from pathlib import Path

from agentpath.types import Message, ToolCall


def default_directory() -> Path:
    return Path(os.environ.get("AGENTPATH_HOME", Path.home() / ".agentpath")) / "sessions"


def to_json(message: Message) -> str:
    return json.dumps(asdict(message), ensure_ascii=False)


def from_json(line: str) -> Message:
    raw = json.loads(line)
    raw["tool_calls"] = [ToolCall(**call) for call in raw.get("tool_calls", [])]
    return Message(**raw)


def safe_name(name):
    """Turn a session name into something that cannot leave the folder.

    The name reaches us from a command line argument, so a name of
    ../../notes would have written outside the sessions directory. Keeping
    only the last part and refusing the two dot names is enough, and it
    keeps the file name readable, which matters because reading these
    files by eye is what they are for.
    """
    last = str(name).replace(chr(92), "/").rstrip("/").split("/")[-1]
    cleaned = "".join(
        character if character.isalnum() or character in "-_." else "-"
        for character in last
    )
    cleaned = cleaned.strip(".-")
    return cleaned or "session"


class Session:
    def __init__(self, name, directory=None):
        self.name = safe_name(name)
        self.path = Path(directory or default_directory()) / f"{self.name}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, message: Message) -> None:
        """Write one message immediately.

        Appending as we go rather than saving at the end is what makes a
        crash survivable. Everything that already happened is on disk.
        """
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(to_json(message) + "\n")

    def load(self) -> list[Message]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [from_json(line) for line in lines if line.strip()]

    @staticmethod
    def list_all(directory=None) -> list[str]:
        folder = Path(directory or default_directory())
        if not folder.is_dir():
            return []
        return sorted(path.stem for path in folder.glob("*.jsonl"))
