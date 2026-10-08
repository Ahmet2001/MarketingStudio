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
```

Each prints notes about what the target cannot do. Read them.

### `tool-schema`

`anthropic_tool.json` and `openai_tool.json`: the workflow as a function-calling tool. A definition only; something has to run the workflow when the model calls it.

### `agent-pack`

A folder the BrowserAgent installs with `/agent pack install`: `plugin.yaml`, `tools/<name>.py`, `env.example`, `README.md`. The tool is **one self-contained file** (runner, workflow, capabilities and engine sources embedded) shaped the way that agent reads tools: a synchronous function named like the tool, real `str/int/float/bool` annotations, the description in the docstring. The workflow id becomes the tool name and must be 3 to 64 lowercase letters, digits or underscores.

The tool returns a dict: `{"status": "ok", "outputs": ..., "run_folder": ...}`, `{"status": "needs_approval", ...}`, or `{"status": "error", "error": ...}`.

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

## Not done yet

An MCP adapter, a `job-spec` adapter for a queue-based runtime, and an install step. Packaging nested workflows. Parallel steps.
