"""The system prompt.

A system prompt does two different jobs and it helps to keep them apart in
your head. The first job is telling the model who it is and how to behave.
The second is telling it facts about the world it cannot see, such as which
directory it is working in and what operating system it is on. Without the
second job the model guesses, and it guesses wrong in ways that waste turns.
"""
import platform
import sys
from pathlib import Path

BEHAVIOUR = """You are a careful software assistant working inside one directory.

Work in small steps. Look before you change anything. When you need to know
what a file contains, read it rather than guessing. When you change a file,
change the smallest amount of text that does the job.

Prefer edit_file over write_file for existing files, because write_file
replaces the whole file and loses anything you did not include.

When you are done, say what you changed in one or two sentences."""


def build_system_prompt(root, extra: str = "") -> str:
    """Assemble the system prompt for a run inside root."""
    facts = [
        f"Workspace directory {Path(root).resolve()}",
        f"Platform {platform.system()}",
        f"Python {sys.version_info.major}.{sys.version_info.minor}",
    ]
    prompt = BEHAVIOUR + "\n\nFacts about this environment\n" + "\n".join(facts)
    if extra:
        prompt += "\n\n" + extra
    return prompt
