"""Saving a conversation so you can come back to it.

The format is one JSON object per line, which is called JSONL. Two things
make it the right choice here.

Each message is written the moment it happens rather than at the end, so a
crash loses nothing that already finished. If you save at the end instead, a
crash after twenty minutes of work loses twenty minutes of work.

And you can open the file and read it. That matters more than it sounds,
because the session file is the first place to look when you want to know
why the agent did something. There is no query language and no viewer to
build. Every question you have about a past run is answered by reading a
text file.

This version supports one writer. Two processes appending to the same
session will interleave their lines and corrupt it. Real harnesses take a
lock. That is left out here because the locking is not the lesson, but the
limit is real.
"""
import json
import os
from pathlib import Path


def default_directory():
    return Path(os.environ.get("AGENTPATH_HOME", Path.home() / ".agentpath")) / "sessions"


class Session:
    def __init__(self, name, directory=None):
        self.name = name
        self.path = Path(directory or default_directory()) / f"{name}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, message):
        """Write one message immediately.

        ensure_ascii is off because the file is for a person to read, and a
        Thai sentence turned into escape codes is not readable.
        """
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")

    def load(self):
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    @staticmethod
    def list_all(directory=None):
        folder = Path(directory or default_directory())
        if not folder.is_dir():
            return []
        return sorted(path.stem for path in folder.glob("*.jsonl"))
