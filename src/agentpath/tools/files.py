"""Tools that let the agent read and change files.

Each tool is a plain function plus a hand written schema, exactly like the
toy tools in lesson 03. The only new idea is that every path goes through
resolve_inside first, so the rules about what may be touched live in one
place instead of being repeated four times.
"""
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.workspace import resolve_inside

MAX_OUTPUT = 4000
SKIP_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", ".ruff_cache"}


def truncate(text: str, limit: int = MAX_OUTPUT) -> str:
    """Keep tool output small enough that it does not eat the context window.

    A single command can produce megabytes. Everything a tool returns is sent
    back to the model on this request and every later one, so an untruncated
    result is paid for many times over.
    """
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[truncated, {len(text) - limit} more characters]"


def file_tools(root) -> list[Tool]:
    """Build the file tools bound to one workspace directory."""
    root = Path(root).resolve()

    def read_file(path):
        target = resolve_inside(root, path)
        if not target.is_file():
            return f"Error: {path} does not exist"
        return truncate(target.read_text(encoding="utf-8", errors="replace"))

    def write_file(path, content):
        target = resolve_inside(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} characters to {path}"

    def edit_file(path, old, new):
        target = resolve_inside(root, path)
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
        target = resolve_inside(root, path)
        if not target.is_dir():
            return f"Error: {path} is not a directory"
        names = []
        for entry in sorted(target.iterdir()):
            if entry.name in SKIP_DIRECTORIES:
                continue
            names.append(entry.name + "/" if entry.is_dir() else entry.name)
        return truncate("\n".join(names) or "(empty directory)")

    return [
        Tool(
            name="read_file",
            description="Read a text file and return its contents.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"}
                },
                "required": ["path"],
            },
            fn=read_file,
            safe=True,
        ),
        Tool(
            name="write_file",
            description=(
                "Write a whole file, creating it if needed. Use edit_file instead when "
                "you only want to change part of an existing file."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"},
                    "content": {"type": "string", "description": "The complete new contents"},
                },
                "required": ["path", "content"],
            },
            fn=write_file,
        ),
        Tool(
            name="edit_file",
            description=(
                "Replace one exact piece of text in a file. The old text must appear "
                "exactly once, so include enough surrounding lines to make it unique."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"},
                    "old": {"type": "string", "description": "The exact text to replace"},
                    "new": {"type": "string", "description": "The text to put in its place"},
                },
                "required": ["path", "old", "new"],
            },
            fn=edit_file,
        ),
        Tool(
            name="list_files",
            description="List the files and directories in one directory.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory relative to the workspace",
                    }
                },
                "required": [],
            },
            fn=list_files,
            safe=True,
        ),
    ]
