import anthropic
from dotenv import load_dotenv

from tools import TOOLS, execute_tool

load_dotenv()

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


def _extract_text(content) -> str:
    # Claude can split its answer across multiple "text" blocks (e.g. one
    # per cited span after a web search) — join them all, don't just take
    # the first one.
    return "".join(block.text for block in content if block.type == "text")


def ask(prompt: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_text(response.content)


def ask_streaming(prompt: str) -> None:
    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        print()


def _announce_tool_use(content) -> None:
    for block in content:
        # "tool_use" = a client-side tool we have to run ourselves (e.g.
        # get_current_time). "server_tool_use" = Anthropic ran it for us
        # already (e.g. web_search) — just here for visibility.
        if block.type in ("tool_use", "server_tool_use"):
            print(f"[Claude is calling tool: {block.name}]")


def ask_with_tools(prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=TOOLS,
        messages=messages,
    )
    _announce_tool_use(response.content)

    # Claude decides on its own whether a question needs a tool. Server-side
    # tools like web_search run and resolve entirely on Anthropic's servers,
    # so they never trigger this loop. Only client-side tools like
    # get_current_time pause here (stop_reason "tool_use") for us to run.
    while response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})

        tool_results = [
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": execute_tool(block.name, block.input),
            }
            for block in response.content
            if block.type == "tool_use"
        ]
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )
        _announce_tool_use(response.content)

    return _extract_text(response.content)


if __name__ == "__main__":
    # print(ask("What is the capital of France?"))
    # print()
    # ask_streaming("Write a haiku about learning to build AI agents.")
    # print()
    prompt = input("Ask Claude something: ")
    print(ask_with_tools(prompt))
