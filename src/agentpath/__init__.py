"""An agent harness you can read in an afternoon.

This file exists so that somebody who installed the package can start
without first learning where everything lives. Until it was written, an
`import agentpath` gave you a version number and nothing else, and a person
wanting an agent had to guess that Agent is in agentpath.agent and that
ToolRegistry is two levels down in agentpath.tools.base.

What is exported here is not everything. It is the list the project's own
command line imports, on the argument that if the CLI needs a name to build
a working agent then so does anybody else building one, and that a name the
CLI never touches has not yet earned a place at the front door.

The deeper paths keep working and stay worth using. `from
agentpath.tools.base import ToolRegistry` says where the thing lives, which
is the whole point of the layout the course builds chapter by chapter. This
is a shortcut for people who already know the shape, not a replacement for
learning it.
"""
from agentpath.agent import Agent
from agentpath.cancel import Cancellation
from agentpath.permissions import Permissions, ask_in_terminal
from agentpath.prompt import build_system_prompt
from agentpath.providers.anthropic import AnthropicProvider
from agentpath.providers.base import Provider
from agentpath.providers.openai_compat import OpenAICompatProvider
from agentpath.session import Session
from agentpath.tools.base import Tool, ToolRegistry
from agentpath.tools.files import file_tools
from agentpath.tools.retrieval import retrieval_tools
from agentpath.tools.search import search_tools
from agentpath.tools.shell import shell_tools
from agentpath.types import (
    Message,
    TextDelta,
    ToolCall,
    ToolCallRequest,
    ToolResult,
    TurnDone,
)

__version__ = "1.0.6"

__all__ = [
    "Agent",
    "AnthropicProvider",
    "Cancellation",
    "Message",
    "OpenAICompatProvider",
    "Permissions",
    "Provider",
    "Session",
    "TextDelta",
    "Tool",
    "ToolCall",
    "ToolCallRequest",
    "ToolRegistry",
    "ToolResult",
    "TurnDone",
    "__version__",
    "ask_in_terminal",
    "build_system_prompt",
    "file_tools",
    "retrieval_tools",
    "search_tools",
    "shell_tools",
]
