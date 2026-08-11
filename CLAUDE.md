# Project notes

## Committing code

Whenever you (Claude) are asked to commit code in this repo, first check whether
`main.py`'s pipeline (the sequence of functions in `ask_with_tools` /
`structure_news` / `render_page`, or the tools in `tools.py`) has changed since
`code_flow.excalidraw` was last generated.

- If the pipeline shape changed, update the node labels/structure in
  `code_flow_diagram.py` to match.
- Then regenerate the diagram: `.venv/bin/python code_flow_diagram.py`
- Include the regenerated `code_flow.excalidraw` in the commit alongside the
  code changes — it's tracked in git (not gitignored), unlike `index.html`
  which is a disposable generated snapshot.

`code_flow_diagram.py` hand-describes the architecture — it does not
introspect `main.py`'s source, so re-running it alone doesn't pick up real
changes. Someone (Claude) has to update the labels when the flow changes.
