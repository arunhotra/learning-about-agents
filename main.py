import html
import json
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from tools import TOOLS, execute_tool

load_dotenv()

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "url": {"type": "string", "description": "The source article URL."},
        "summary": {
            "type": "string",
            "description": "A detailed, multi-sentence summary covering the full article.",
        },
    },
    "required": ["headline", "url", "summary"],
    "additionalProperties": False,
}

NEWS_SCHEMA = {
    "type": "object",
    "properties": {
        "main_story": STORY_SCHEMA,
        "secondary_stories": {"type": "array", "items": STORY_SCHEMA},
    },
    "required": ["main_story", "secondary_stories"],
    "additionalProperties": False,
}


def _extract_text(content) -> str:
    # Claude can split its answer across multiple "text" blocks (e.g. one
    # per cited span after a web search) — join them all, don't just take
    # the first one. Each block can also carry "citations" pointing at the
    # real URL a span came from — inline those as [Source: url] markers so
    # downstream code has a grounded URL instead of a Claude-remembered one.
    parts = []
    for block in content:
        if block.type != "text":
            continue
        parts.append(block.text)
        for citation in block.citations or []:
            url = getattr(citation, "url", None)
            if url:
                parts.append(f" [Source: {url}]")
    return "".join(parts)


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
        max_tokens=2048,
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


def structure_news(raw_text: str) -> dict:
    # A separate, tool-free call: structured outputs guarantee the response
    # is valid JSON matching NEWS_SCHEMA, so there's nothing to parse or
    # guess at — just json.loads() the text block. This call only
    # *reorganizes* raw_text into JSON; it doesn't add new facts, so the
    # detail and URLs have to already be present in raw_text.
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        output_config={"format": {"type": "json_schema", "schema": NEWS_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    "Pick the single most important story as the main story, "
                    "and the other two as secondary stories. Keep each "
                    "summary's full detail — don't shorten it. Each source "
                    "URL appears inline as '[Source: url]' right after the "
                    "text it supports — use the URL from the marker nearest "
                    "that story as its url field, and don't include the "
                    f"'[Source: ...]' marker itself in the summary text:\n\n{raw_text}"
                ),
            }
        ],
    )
    return json.loads(_extract_text(response.content))


def render_page(news: dict) -> None:
    template = Path("template.html").read_text()
    secondary = news["secondary_stories"]

    page = (
        template.replace("{{MAIN_HEADLINE}}", html.escape(news["main_story"]["headline"]))
        .replace("{{MAIN_URL}}", html.escape(news["main_story"]["url"]))
        .replace("{{MAIN_SUMMARY}}", html.escape(news["main_story"]["summary"]))
        .replace("{{SECOND_HEADLINE}}", html.escape(secondary[0]["headline"]))
        .replace("{{SECOND_URL}}", html.escape(secondary[0]["url"]))
        .replace("{{SECOND_SUMMARY}}", html.escape(secondary[0]["summary"]))
        .replace("{{THIRD_HEADLINE}}", html.escape(secondary[1]["headline"]))
        .replace("{{THIRD_URL}}", html.escape(secondary[1]["url"]))
        .replace("{{THIRD_SUMMARY}}", html.escape(secondary[1]["summary"]))
    )

    Path("index.html").write_text(page)


if __name__ == "__main__":
    prompt = (
        "Give me the 3 most important pieces of news from today, focus on "
        "the tech sector only. For each story, write a detailed summary "
        "covering the key facts, context, and why it matters — a full "
        "paragraph, not just a headline."
    )
    raw_news = ask_with_tools(prompt)
    print(raw_news)
    print()

    news = structure_news(raw_news)
    print(json.dumps(news, indent=2))

    render_page(news)
    print("\nWrote index.html")
