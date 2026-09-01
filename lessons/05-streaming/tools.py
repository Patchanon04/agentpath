"""Toy tools with hand written schemas.

The tools are deliberately boring. A calculator and a dice roll have results
you can predict, so when something goes wrong you know the problem is in the
plumbing and not in the tool.

The schema below is JSON Schema. It is the only thing the model ever sees
about your function, so every word in the description is doing work.
"""
import random

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers together and return the sum.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "Roll a dice with the given number of sides.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sides": {"type": "integer", "description": "How many sides the dice has"}
                },
                "required": ["sides"],
            },
        },
    },
]


def add(a, b):
    return a + b


def roll_dice(sides):
    return random.randint(1, sides)


FUNCTIONS = {"add": add, "roll_dice": roll_dice}


def run(name, arguments):
    """Run one tool by name and return its result as a string."""
    function = FUNCTIONS.get(name)
    if function is None:
        return f"Error: unknown tool {name}"
    try:
        return str(function(**arguments))
    except Exception as error:
        return f"Error: {type(error).__name__}: {error}"
