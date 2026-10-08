# Workflow viewer (experimental)

A local, read-only browser page for looking at what the `studio` package has: the workflows you wrote, the capabilities they use, and exactly what each export format produces. It is an **experiment**, self-contained in this folder; nothing else in the repository imports it.

```bash
apps/studio-api/.venv/bin/python -m ui --sources examples/single_file examples/text_report engines
# then open http://127.0.0.1:8765
```

Any Python with PyYAML works. There is no build step and no `npm install`.

## What you can do

- **Workflows**: every workflow file under the root, with its state (valid or how many problems, needs approval). Open one to see its inputs, its steps in run order with the capability and approval for each, its outputs, and whether this machine is ready to run it (missing keys, programs, packages; estimated cost).
- **Export**: pick `bundle`, `agent-pack`, `tool-schema`, `job-handler`, `worker` or `mcp`. The page builds it and shows the file list, the notes the adapter prints, and the content of every file. Download the whole thing as a zip. If an adapter refuses (for example a workflow id that is too short for an agent tool name) you see its message.
- **Capabilities**: the catalogue from your sources, with inputs, outputs, requirements and permissions.

## Boundaries

- Read-only. It runs nothing and writes nothing; there is no save and no run endpoint (the tests check that).
- It adds no workflow logic: validation, planning and the adapters are the `studio` functions.
- The server listens on `127.0.0.1` only, refuses other `Host`/`Origin` headers, and opens only `.yaml` files under `--root` (default: the repository).
- Authoring stays in files and the `studio` command line (`studio new`, `validate`, `plan`, `run`).

## Removing it

Delete this folder (`rm -rf ui`) and the one-line mention in the main README. Nothing else refers to it.

## Tests

```bash
apps/studio-api/.venv/bin/python -m pytest ui
```

They test the server (listing, detail, every export target, path safety, host/origin checks). The page itself was checked by driving it in a real browser; that script is not part of the repository.
