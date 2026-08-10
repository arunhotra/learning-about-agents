from datetime import datetime

TOOLS = [
    {
        "name": "get_current_time",
        "description": "Get the current date and time.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # Server-side tool — Anthropic runs the search itself, so there's no
    # matching Python function or TOOL_FUNCTIONS entry below.
    {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 3,
    },
]


def get_current_time() -> str:
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")


TOOL_FUNCTIONS = {
    "get_current_time": get_current_time,
}


def execute_tool(name: str, tool_input: dict) -> str:
    if name not in TOOL_FUNCTIONS:
        return f"Unknown tool: {name}"
    return TOOL_FUNCTIONS[name](**tool_input)
