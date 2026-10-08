# Bundles and adapters

Studio and the thing that uses a workflow usually run on different machines with different Python setups. So a workflow leaves the factory as a **bundle** that needs nothing installed, and **adapters** reshape that bundle for one kind of consumer. Adapters only write files. They never connect to, install into, or call anything.

```
workflow.yaml ──bundle──► folder that runs on its own ──adapt──► files one consumer reads
```

## Bundle

```bash
python -m studio bundle workflow.yaml --sources ./my_tools --out ./bundle
python bundle/portable.py bundle --input topic="..." --approve upload      # run it anywhere
```

| File | Contents |
|---|---|
| `portable.py` | The runner. Python standard library only. |
| `workflow.json`, `capabilities.json`, `bases.json`, `manifest.json` | The validated workflow, what it uses, and what it needs and may do |
| `engines/` | Source of every single-file engine the workflow uses |
| `requirements.txt` | Packages the engines declare |

Two kinds of step:

- **Inline**: single-file engines. Their source travels in the bundle, so they run anywhere.
- **External**: command-line engines and the like (for example `story-video`). They are not copied. The bundle records where they were found and checks on the running machine that they exist; `STUDIO_DIR_<CAPABILITY_ID>` points at another folder. An `http` capability, or a capability that is itself a workflow, cannot be bundled yet.

## Adapters

```bash
python -m studio adapt workflow.yaml --target agent-pack  --out ./pack   --sources ./my_tools
python -m studio adapt workflow.yaml --target tool-schema --out ./schema --sources ./my_tools
python -m studio adapt workflow.yaml --target job-handler --out ./handler --sources ./my_tools
python -m studio adapt workflow.yaml --target worker      --out ./worker  --sources ./my_tools
python -m studio adapt workflow.yaml --target mcp         --out ./mcp     --sources ./my_tools
```

The first two, and `mcp`, make the workflow a **tool** a model calls. The last two make it an **item a worker runs**: `job-handler` is one file you plug into a worker you already have, `worker` is a whole process that serves a queue.

Each prints notes about what the target cannot do. Read them.

### `tool-schema`

`anthropic_tool.json` and `openai_tool.json`: the workflow as a function-calling tool. A definition only; something has to run the workflow when the model calls it.

### `agent-pack`

A folder the BrowserAgent installs with `/agent pack install`: `plugin.yaml`, `tools/<name>.py`, `env.example`, `README.md`. The tool is **one self-contained file** (runner, workflow, capabilities and engine sources embedded) shaped the way that agent reads tools: a synchronous function named like the tool, real `str/int/float/bool` annotations, the description in the docstring. The workflow id becomes the tool name and must be 3 to 64 lowercase letters, digits or underscores.

Checked against the BrowserAgent's own code (in a scratch copy, nothing in that project was touched): its pack preview reports the pack installable, `install_agent_pack` installs it, its loader finds the function, and its schema builder sees real `integer`/`boolean` parameters. Two things found that way are handled in the generated file: the agent compiles tool files with `from __future__ import annotations` in force, which would make every parameter look like a string (the file pins the real types), and a model may pass `approve` as the text `"false"` (anything but a true-like value does not approve).

The tool returns a dict: `{"status": "ok", "outputs": ..., "run_folder": ...}`, `{"status": "needs_approval", ...}`, or `{"status": "error", "error": ...}`.

### `job-handler`

`handler.py`, `job.schema.json`, `README.md`. One file, standard library only, with the runner, workflow, capabilities and single-file engines embedded. It does not poll or listen; a worker that already has jobs calls it.

```python
import handler
result = handler.handle(job["payload"]["inputs"], approved_steps=job.get("approved_steps", []))
```

From a worker in another language, run it as a process: `echo '{"inputs": {...}, "approved_steps": []}' | python handler.py` and read one JSON object from stdout.

The result is `{"status": "done", "outputs": ..., "run_folder": ...}`, `{"status": "awaiting_approval", "gated_steps": [...]}` (nothing ran) or `{"status": "failed", "error": ...}`. **Approval is per step**: a step that writes to the outside world runs only when its id is in `approved_steps`.

### `mcp`

A folder: `server.py` (standard library only), `handler.py`, `mcp.json` and `README.md`. `server.py` is a Model Context Protocol server over **stdio**: an MCP client starts it as a command (`python server.py`) and sees one tool, named after the workflow, whose arguments are the workflow inputs. It is not an HTTP server.

The tool returns one JSON text block with the handler's result (`done`, `awaiting_approval` or `failed`; `isError` is set on `failed`). Engines' `print` output goes to stderr so it cannot corrupt the protocol. Runs are synchronous: a long run blocks the server until it ends.

Approval is the tool argument `approve`, the same convention as `agent-pack`: gated steps run only when it is `true` (the text `"false"` does not count), and the client has to respect that. For an enforced gate use `worker`.

### `worker`

A folder: `worker.py` (standard library only), `handler.py`, `job.schema.json`, `migrations/001_<id>_jobs.sql`, `.env.example`, `Dockerfile`, `README.md` (and `requirements.txt` if engines declare packages). Run it with `python worker.py` (`--once` to process what is queued and exit).

Two queues, chosen with `WORKER_BACKEND`:

| Queue | How it works |
|---|---|
| `file` (default) | Jobs are JSON files that move between `queued/`, `processing/`, `awaiting_approval/`, `done/` and `failed/`. Claiming is an atomic rename, so several workers can share a folder. Nothing to install. |
| `supabase` | The `<id>_jobs` table over REST, in the shape of the existing `*_jobs` tables: `status`, `payload`, `results`, `error`, `attempts`, timestamps, and a claim function using `for update skip locked`. The migration is generated. |

A job's `payload` is exactly `{"inputs": {...}}`; any other field fails the job. Results have secret-looking environment values removed before they are stored.

**Approval is held by the queue.** A job for a workflow with gated steps stops in `awaiting_approval` and nothing runs. An operator adds the step ids to `approved_steps` and puts the job back in `queued`. That is a real gate only if whoever creates jobs cannot write `approved_steps` or `status`: the migration includes the column-level grants that make this so (commented out; adapt the role names). With the file queue it depends on who can write to the folders.

### Using it inside a worker you already run

Take `job-handler`. Your worker keeps its own queue, credentials and scheduling and calls the handler for the jobs of this workflow. The factory does not edit other projects' workers.

- A worker written in Python can import `handler.py`.
- A worker in another language can start it as a process.
- Do not route workflows that write to the outside world through a worker whose design forbids writes. For example, `platform_data_worker` in marketing-agent-assets runs only a hand-written, read-only allowlist of toolbox functions; a workflow is not one of those, and adding one means changing that worker's policy on purpose.

## File inputs

A `file:*` input of a bundle or generated tool is a **reference**, in one of these forms:

| Form | Rule |
|---|---|
| `https://...` | Downloaded. https only, public hosts only (private and loopback addresses and redirects to them are refused), at most `STUDIO_MAX_FILE_MB` (default 100). |
| `{"filename": ..., "content_base64": ...}` | Written into the run folder. Same size limit; the filename is reduced to a safe name. |
| `asset:<id>` | Resolved by a function the host provides (`FilePolicy.asset_resolver`). Refused when none is configured. |
| A local path | **Refused by default**, so a caller cannot read arbitrary files. Allowed only inside the folders listed in `STUDIO_FILE_ROOTS`. |

`python -m studio run` is for a person at their own terminal, so it accepts any local path. File outputs are returned as paths on the machine that ran the workflow.

Known limit: the host name is checked before the download starts, so a DNS answer that changes in between is not caught.

## Approval

A step that writes to the outside world needs approval. In a bundle run, name the step with `--approve`. In a generated tool, the tool refuses to start (returning `needs_approval`) until it is called with `approve=true`, and its description tells the model to ask the user first. **This is a convention, not a lock**: nothing stops a model from passing `approve=true` on its own. If you need a hard gate, enforce it where the tool is called.

## Where the generated tool runs things

`STUDIO_TOOL_HOME` (default: the system temp folder, `studio_tools/`). Each call has its own run folder, returned as `run_folder`.

## Your own libraries (torch, anything)

Your engines can import whatever is installed where they run. `portable.py` itself needs only the standard library; that limit does not apply to engines.

- **Python engines** run in the same Python as the runner (for an agent pack, the agent's Python). Install their libraries there.
- **Command-line engines** run the command in their capability file. A bare `python` or `python3` there means the machine's default Python; set `STUDIO_PYTHON=/path/to/venv/bin/python` to make every bare `python` command use another interpreter (for example a virtual environment that has torch).
- Declare what an engine needs: `"packages": ["torch>=2.1"]` (or `requires.packages` in a `capability.yaml`). Before any step runs, the runner checks each package is installed for the interpreter that will use it and stops with a message naming the missing ones. Only the presence of the package is checked, not its version.
- Studio never installs packages. Declared packages are listed in the bundle's `requirements.txt` and in the pack README.
- Import heavy libraries inside the function, so merely reading or checking the engine file never loads them.
- Model weights are not copied into a bundle; only the engine's source is.

## Not done yet

An MCP adapter and an install step. Packaging nested workflows. Parallel steps.
