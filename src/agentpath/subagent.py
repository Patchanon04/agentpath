"""Turning a whole agent into a single tool the parent can call.

There is no new machinery here. A subagent is a tool whose implementation
happens to run another agent. The parent sees a tool with a name and a
description, exactly like read_file, and the loop does not change at all.
That is the point worth noticing rather than the code.

The reason to want one is context. A long investigation fills a
conversation with dozens of tool results that the parent never needs to see
again once the question is answered. Handing that job to a child means the
parent gets the answer and none of the searching.

The same isolation is also the trap. The child and the parent hold separate
views of the world, so a file the child changed is still the old file as far
as the parent is concerned. Nothing tells the parent it is now wrong.
"""
from agentpath.tools.base import Tool
from agentpath.types import TurnDone

DEFAULT_DESCRIPTION = (
    "Hand a self contained job to a separate agent and get back only its final "
    "answer. Use this for work that needs many steps of searching or reading, "
    "when you want the conclusion and not the whole investigation. Describe the "
    "job completely, because the other agent cannot see this conversation."
)


def run_to_completion(agent, task):
    """Run an agent and return the text it finished with."""
    answer = ""
    for event in agent.run(task):
        if isinstance(event, TurnDone):
            answer = event.message.content
    return answer


def subagent_tool(build_agent, name="run_subagent", description=None, safe=False) -> Tool:
    """Build the tool.

    build_agent is a function returning a fresh Agent rather than an Agent
    itself. That is deliberate. A subagent that kept its history between
    calls would slowly accumulate the same clutter it exists to prevent, and
    the second call would start from wherever the first one happened to end.
    """

    def run_subagent(task):
        child = build_agent()
        try:
            answer = run_to_completion(child, task)
        except Exception as error:
            # A child that fails must not take the parent with it. The parent
            # can read this, decide the approach did not work, and try
            # something else, which is exactly what a person would do.
            return f"Error: the subagent failed, {type(error).__name__}: {error}"
        return answer or "The subagent finished without saying anything."

    return Tool(
        name=name,
        description=description or DEFAULT_DESCRIPTION,
        parameters={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The complete job, written so it makes sense on its own",
                }
            },
            "required": ["task"],
        },
        fn=run_subagent,
        safe=safe,
    )
