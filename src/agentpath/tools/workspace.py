"""One place that decides which paths a tool is allowed to touch.

Every file tool goes through resolve_inside. Having exactly one gate is what
makes the rule reviewable. A rule spread across four tools is a rule that one
of them will forget.
"""
from pathlib import Path

SECRET_NAMES = {".env", "id_rsa", "id_ed25519", ".npmrc", ".netrc", "credentials"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SECRET_PREFIXES = (".env.",)


class WorkspaceError(Exception):
    """Raised when a tool asks for a path it is not allowed to have."""


def looks_like_a_secret(name: str) -> bool:
    lowered = name.lower()
    if lowered in SECRET_NAMES:
        return True
    if lowered.startswith(SECRET_PREFIXES):
        return True
    return Path(lowered).suffix in SECRET_SUFFIXES


def resolve_inside(root, path) -> Path:
    """Turn a path from the model into a real path inside root, or refuse.

    Two separate refusals happen here. The first stops the agent reaching
    outside its workspace at all, which covers both parent directory escapes
    and absolute paths. The second stops it reading credential files that
    happen to live inside the workspace, because anything a tool reads is
    sent to the model provider on every later request and stays in the
    conversation from then on.
    """
    root = Path(root).resolve()
    candidate = (root / Path(path)).resolve()
    if candidate != root and not candidate.is_relative_to(root):
        raise WorkspaceError(f"{path} is outside the workspace")
    if looks_like_a_secret(candidate.name):
        raise WorkspaceError(
            f"this tool refuses to read {candidate.name} because credential files "
            "must not enter the conversation"
        )
    return candidate
