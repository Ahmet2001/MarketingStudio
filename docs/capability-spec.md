# Capability spec (v0.1)

A capability is something the Studio can run: a pipeline, an API call, or a function. Each one is described in a `capability.yaml` file that sits next to the code. The file is the contract: what the capability does, what it takes, what it gives back, what it needs, and whether it touches the outside world.

Adding a `capability.yaml` never changes the code it describes. If the file is deleted, the engine still runs exactly as before; the Studio just no longer knows about it.

## Where the files are

| File | Capabilities |
|---|---|
| [engines/story-video/capability.yaml](../engines/story-video/capability.yaml) | `story.video.generate` |
| [engines/documentary-video/capability.yaml](../engines/documentary-video/capability.yaml) | `documentary.video.generate` |
| [engines/local-image/capability.yaml](../engines/local-image/capability.yaml) | `image.storyboard.local` |
| [engines/product-ads/capability.yaml](../engines/product-ads/capability.yaml) | `ad.creative.generate`, `ad.creative.revise`, `ad.creative.approve` |
| [connectors/capability.yaml](../connectors/capability.yaml) | `social.search.*`, `social.publish.*` |

Check every file with `python scripts/validate_capabilities.py`.

## File shape

```yaml
spec_version: "0.1"
capabilities:
  - id: story.video.generate          # unique, lowercase, dot separated
    version: 0.1.0
    title: Story video
    description: One sentence on what it does.
    status: working                   # working | experimental | planned
    inputs:
      topic: {type: text, required: true, description: ...}
      duration: {type: integer, default: 45}
    outputs:
      video: {type: "file:mp4", description: ...}
    requires:
      env: [GEMINI_API_KEY]           # environment variables / credentials
      binaries: [ffmpeg]              # programs on PATH
      hardware: []                    # e.g. cuda-gpu
    permissions:
      network: true                   # calls external services
      writes_external_state: false    # posts, sends, uploads, edits remote data
      requires_approval: false        # true forces a human approval step
    cost:
      estimate_usd: null              # null = not measured yet
      notes: ...
    execution:
      type: cli                       # cli | http | python
      ...                             # type specific, see below
    failure_modes:
      - ...
```

### Input and output types

`any` (matches every type), `text`, `integer`, `number`, `boolean`, `enum` (with `values`), `url`, `list`, `object`, and `file:<ext>` (for example `file:mp4`, `file:png`, `file:image`). A workflow may connect an output to an input only when the types match, so `file:mp4` can feed `file:mp4` but not `text`.

### Execution types

- **cli:** `cwd`, `command` (list), `positional` (input names in order), `flags` (input name to flag), `output_dir_flag`, and `outputs` mapping each output to a path pattern.
- **http:** `base_url_env` or `base_url`, and an `operations` list (`method`, `path`).
- **python:** `module` and `function` per capability, for the connectors.
- **workflow:** `definition`, the path of a `workflow.yaml` next to the file. See below.

### Permissions

`writes_external_state: true` means the capability changes something outside this machine: it publishes, comments, messages, or uploads. Such capabilities must also set `requires_approval: true`. The validator enforces this.

## Relation to MarketingAssets

Connector actions are named after the toolbox manifests in `marketing-agent-assets/toolboxes/*/manifest.yaml` (`required_env`, `function_prefixes`) so the two stay easy to map. This spec is deliberately small; the plan is to align it with the shared JSON schemas there (`publish_request`, `asset`) once the Studio and the worker agree on one execution path.

## Honest limits

- Costs are `null` until measured. No numbers are guessed.
- Nothing reads these files yet. They are the contract; wiring `modes.py`, the workflow validator and the agent API to them is the next step.

## Workflows exported as capabilities

Workflows are written freely as files; see [workflows.md](workflows.md). This section describes what their export contains.

A saved workflow can be exported as two files that depend on nothing but this spec:

| File | Contains |
|---|---|
| `workflow.yaml` | `inputs`, ordered `steps`, and `outputs`. Each step names a `capability`, lists `needs`, passes `with` values, and carries `approval: required` when the capability writes to the outside world. |
| `capability.yaml` | The whole workflow as one capability (`id: workflow.<name>`, `execution.type: workflow`). Inputs, outputs, `requires`, permissions and failure modes are merged from the steps. |

Values inside `with` and `outputs` use only two reference forms: `"{{ inputs.<name> }}"` and `"{{ steps.<step>.outputs.<name> }}"`.

Merge rules for the generated capability: `requires` is the union of the steps; `writes_external_state` and `network` are true when any step sets them; `requires_approval` is true whenever any step writes externally; `cost.estimate_usd` is the sum, or `null` when any step is unmeasured.

The exporter refuses a workflow instead of guessing: an unknown content generator, a destination with no capability, or a step output whose type does not match the next step's input (for example a local `file:mp4` into an input that needs a public `url`) is an error with an explanation.

### Nodes carry a capability_id

Every workflow node can name the capability it runs with `capability_id` (for example `story.video.generate`). Rules:

- The id must exist in the registry, otherwise saving the workflow fails with a 422 that names it.
- A content-generator node's id must match its mode, because a run is still driven by the mode. A contradiction is refused instead of silently ignored.
- Nodes saved without an id get one filled in from their old subtype when the workflow is saved again. Older stored workflows are still exported correctly because the exporter falls back to the same mapping.
- Config keys on a generator that are inputs of its capability (for example `seed`) are fixed values in the exported step; the common ones (`topic`, `language`, `duration`, `scenes`, `niche`) become workflow inputs.

`GET /api/capabilities` lists the registry and `GET /api/modes` now includes each mode's `capability_id`.

Scheduling is not part of an exported tool. Whoever calls the tool decides when it runs, so scheduler nodes are dropped with a warning.

Export through the API (`GET /api/workflows/{id}/export`) or the command line:

```bash
cd apps/studio-api
python -m app.exporter <workflow_id> --out ./exported
```

The exporter has no knowledge of any agent or runtime. Turning these files into something a specific consumer reads is a separate, later step.
