"""Deciding what the agent is allowed to do, and remembering the answer.

Lesson 08 asked a yes or no question before every command. That is correct
and it is also unusable, because being asked to approve the same harmless
command forty times trains you to stop reading the question. By the tenth
time you are pressing y before the text has finished printing, which means
the gate is still there and is no longer protecting you.

A permission system is what you get when you keep the gate and remove the
fatigue. Three things change.

Reading is not writing. Listing files or reading one cannot destroy
anything, so those never ask at all.

The answer has three options rather than two. Yes, no, and yes and stop
asking me about this exact thing.

What gets remembered is the exact call, arguments included. Approving
git status must never also approve rm -rf, and a rule stored under the tool
name alone would do exactly that.
"""
import json

ALLOW_ONCE = "allow_once"
ALLOW_ALWAYS = "allow_always"
DENY = "deny"

# Tools that cannot change anything. Reading is always allowed.
# A tool missing from this set is treated as dangerous, which is the safe
# direction to be wrong in.
SAFE_TOOLS = {"read_file", "list_files", "glob_files", "grep_files"}


def signature(name, arguments):
    """A stable string identifying this exact call, used for remembering."""
    return f"{name}({json.dumps(arguments, sort_keys=True)})"


def loose_signature(name, arguments):
    """The same idea as signature, but blind to whitespace and letter case.

    This one is for spotting a model going in circles, not for deciding what
    is allowed. A model that retries with a trailing space added, or with a
    word capitalised, has not changed anything and should not get a fresh
    fingerprint for it. Permission decisions keep using the exact signature,
    because there the difference between two nearly identical commands can be
    the whole point.
    """
    # Trailing and leading space only. Folding case as well made three
    # genuinely different searches look identical, and a model widening a
    # pattern from Error to error was told it was going in circles.
    flattened = {key: str(value).strip() for key, value in arguments.items()}
    return f"{name}({json.dumps(flattened, sort_keys=True)})"

class Permissions:
    def __init__(self, ask=None, auto_approve=False):
        self.ask = ask
        self.auto_approve = auto_approve
        self.remembered = set()

    def check(self, name, arguments):
        """Say whether this call may run, asking a person only when needed."""
        if name in SAFE_TOOLS:
            return True
        if self.auto_approve:
            return True
        if signature(name, arguments) in self.remembered:
            return True
        if self.ask is None:
            return False
        answer = self.ask(name, arguments)
        if answer == ALLOW_ALWAYS:
            self.remembered.add(signature(name, arguments))
            return True
        return answer == ALLOW_ONCE


def ask_in_terminal(name, arguments):
    """Ask the person at the keyboard, offering the three real answers."""
    print(f"\nThe agent wants to run {name}")
    for key, value in arguments.items():
        print(f"  {key} = {value!r}")
    try:
        answer = input("Allow? [y]es once, [a]lways for this exact call, [N]o ")
    except (EOFError, KeyboardInterrupt):
        print()
        return DENY
    answer = answer.strip().lower()
    if answer in ("a", "always"):
        return ALLOW_ALWAYS
    if answer in ("y", "yes"):
        return ALLOW_ONCE
    return DENY
