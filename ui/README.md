# Workflow editor (experimental)

A local, browser-based editor for the workflow files the `studio` package reads and writes. It is an **experiment**: it is self-contained in this folder, and nothing else in the repository imports it.

```bash
apps/studio-api/.venv/bin/python -m ui --sources examples/single_file examples/text_report engines
# then open http://127.0.0.1:8765
```

Any Python with PyYAML works. There is no build step and no `npm install`.

## What it does

- **Palette** (left): every capability the sources define. Drag one onto the canvas, or double-click it.
- **Canvas**: steps are nodes. Drag from a right dot to a left dot to connect an output to an input (this writes `{{ steps.a.outputs.b }}`). Drag from a "Workflow inputs" dot to use a workflow input. Double-click a line to remove it. `Delete` removes the selected step.
- **Inspector** (right): edit the selected step (id, inputs, approval), the workflow's inputs and outputs, or its id and name.
- **Bottom panel**: *Problems* (live validation), *Plan* (order, approvals, what is missing here, cost), *Run* (runs on this machine, with approval checkboxes for steps that write outside), *Export* (every adapter, downloaded as a zip), *YAML* (see and edit the file text).

It edits plain `workflow.yaml` files, so you can edit the same file by hand or with the `studio` command line.

## Boundaries

- It adds **no workflow logic**: validation, planning, running, bundling and the adapters are the `studio` functions.
- The server listens on `127.0.0.1` only, refuses other `Host`/`Origin` headers, and opens or saves only `.yaml` files under `--root` (default: the repository).
- Node positions are kept outside the workflow file, in `ui/layouts/` (git-ignored), so workflow files stay clean.
- Running a workflow here runs it for real, with your environment and keys. Steps that change something outside the machine need their checkbox ticked in the *Run* tab.

## Removing it

Delete this folder (`rm -rf ui`) and the one-line mention in the main README. Nothing else refers to it.

## Tests

```bash
apps/studio-api/.venv/bin/python -m pytest ui
```

These test the server (API, path safety, host/origin checks, run, export). The page itself was checked by driving it in a real browser; that script is not part of the repository.
