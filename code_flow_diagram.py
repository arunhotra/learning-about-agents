"""
Generates code_flow.excalidraw — a diagram of main.py's pipeline.
Run it directly: .venv/bin/python code_flow_diagram.py
Then open code_flow.excalidraw at https://excalidraw.com (drag the file in,
or File > Open).
"""

import json
import random
import textwrap
import time
from pathlib import Path

FONT_FAMILY = 1  # Excalidraw's hand-drawn font
STROKE = "#1e1e1e"


def _id() -> str:
    return f"el_{random.randint(10**8, 10**9 - 1)}"


def _base(el_type: str, x: float, y: float, width: float, height: float, **overrides) -> dict:
    element = {
        "id": _id(),
        "type": el_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": STROKE,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": random.randint(1, 2**31 - 1),
        "version": 1,
        "versionNonce": random.randint(1, 2**31 - 1),
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
    }
    element.update(overrides)
    return element


def box(x: float, y: float, width: float, height: float, background: str) -> dict:
    return _base(
        "rectangle", x, y, width, height,
        backgroundColor=background,
        roundness={"type": 3},
    )


def label(x: float, y: float, width: float, text: str, font_size: int = 16) -> dict:
    chars_per_line = max(int(width / (font_size * 0.55)), 10)
    wrapped_lines = []
    for line in text.split("\n"):
        wrapped_lines.extend(textwrap.wrap(line, width=chars_per_line) or [""])
    wrapped = "\n".join(wrapped_lines)
    return _base(
        "text", x, y, width, len(wrapped_lines) * font_size * 1.25,
        text=wrapped,
        originalText=text,
        fontSize=font_size,
        fontFamily=FONT_FAMILY,
        textAlign="left",
        verticalAlign="top",
        lineHeight=1.25,
    )


def arrow(points: list[tuple[float, float]]) -> dict:
    x0, y0 = points[0]
    rel_points = [[px - x0, py - y0] for px, py in points]
    xs = [p[0] for p in rel_points]
    ys = [p[1] for p in rel_points]
    return _base(
        "arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys),
        points=rel_points,
        lastCommittedPoint=None,
        startBinding=None,
        endBinding=None,
        startArrowhead=None,
        endArrowhead="triangle",
        roundness={"type": 2},
    )


def node(elements: list, x: float, y: float, width: float, height: float, text: str, color: str) -> tuple:
    elements.append(box(x, y, width, height, color))
    elements.append(label(x + 16, y + 12, width - 32, text, font_size=16))
    return x, y, width, height


def bottom_center(n):
    x, y, w, h = n
    return (x + w / 2, y + h)


def top_center(n):
    x, y, w, h = n
    return (x + w / 2, y)


def build() -> dict:
    elements = []
    W = 420
    X = 260
    GAP = 60

    elements.append(label(40, 20, 900, "learning-about-agents -- code flow (main.py)", font_size=28))

    y = 100
    n_prompt = node(elements, X, y, W, 70,
                     "Static prompt (in __main__):\n\"Give me the 3 most important tech news stories...\"",
                     "#e9ecef")

    y += 70 + GAP
    n_ask = node(elements, X, y, W, 90,
                 "ask_with_tools(prompt)\nsends prompt + TOOLS to\nclient.messages.create(...)",
                 "#a5d8ff")

    y += 90 + GAP
    n_loop = node(elements, X, y, W, 110,
                  "while response.stop_reason == \"tool_use\":\nrun the tool, send tool_result back,\nask Claude again",
                  "#ffd8a8")

    # tools.py side box, feeding into the loop
    tools_x = X + W + 140
    n_tools = node(elements, tools_x, y - 10, 320, 220,
                   "tools.py\n\nTOOLS list +\nexecute_tool(name, input)\n\n- get_current_time\n  (client-side: we run it)\n- web_search\n  (server-side: Anthropic\n  runs it, we just declare it)",
                   "#eebefa")
    elements.append(arrow([(tools_x, y + 60), (X + W, y + 55)]))

    # self-loop arrow on the tool-use loop box
    lx, ly, lw, lh = n_loop
    elements.append(arrow([
        (lx + lw, ly + lh * 0.3),
        (lx + lw + 55, ly + lh * 0.3),
        (lx + lw + 55, ly + lh * 0.7),
        (lx + lw, ly + lh * 0.7),
    ]))
    elements.append(label(lx + lw + 5, ly + lh + 6, 140, "loops until no\nmore tool calls", font_size=13))

    y += 110 + GAP
    n_raw = node(elements, X, y, W, 90,
                 "raw_news = _extract_text(response.content)\njoins all text blocks + inlines\ncitation URLs as [Source: url]",
                 "#b2f2bb")

    y += 90 + GAP
    n_structure = node(elements, X, y, W, 90,
                        "structure_news(raw_news)\na SECOND, tool-free call using\noutput_config: json_schema",
                        "#a5d8ff")

    y += 90 + GAP
    n_json = node(elements, X, y, W, 70,
                   "news = {\n  main_story, secondary_stories: [...]\n} (headline, url, summary each)",
                   "#ffec99")

    y += 70 + GAP
    n_render = node(elements, X, y, W, 70,
                     "render_page(news)\nreads template.html, replaces\n{{PLACEHOLDER}} markers",
                     "#a5d8ff")

    y += 70 + GAP
    n_html = node(elements, X, y, W, 60,
                   "index.html\n(generated output, gitignored)",
                   "#e9ecef")

    for a, b in [
        (n_prompt, n_ask), (n_ask, n_loop), (n_loop, n_raw),
        (n_raw, n_structure), (n_structure, n_json),
        (n_json, n_render), (n_render, n_html),
    ]:
        elements.append(arrow([bottom_center(a), top_center(b)]))

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


if __name__ == "__main__":
    scene = build()
    Path("code_flow.excalidraw").write_text(json.dumps(scene, indent=2))
    print(f"Wrote code_flow.excalidraw ({len(scene['elements'])} elements)")
