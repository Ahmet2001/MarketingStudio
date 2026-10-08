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

`text`, `integer`, `number`, `boolean`, `enum` (with `values`), `url`, `list`, `object`, and `file:<ext>` (for example `file:mp4`, `file:png`, `file:image`). A workflow may connect an output to an input only when the types match, so `file:mp4` can feed `file:mp4` but not `text`.

### Execution types

- **cli:** `cwd`, `command` (list), `positional` (input names in order), `flags` (input name to flag), `output_dir_flag`, and `outputs` mapping each output to a path pattern.
- **http:** `base_url_env` or `base_url`, and an `operations` list (`method`, `path`).
- **python:** `module` and `function` per capability, for the connectors.

### Permissions

`writes_external_state: true` means the capability changes something outside this machine: it publishes, comments, messages, or uploads. Such capabilities must also set `requires_approval: true`. The validator enforces this.

## Relation to MarketingAssets

Connector actions are named after the toolbox manifests in `marketing-agent-assets/toolboxes/*/manifest.yaml` (`required_env`, `function_prefixes`) so the two stay easy to map. This spec is deliberately small; the plan is to align it with the shared JSON schemas there (`publish_request`, `asset`) once the Studio and the worker agree on one execution path.

## Honest limits

- Costs are `null` until measured. No numbers are guessed.
- Nothing reads these files yet. They are the contract; wiring `modes.py`, the workflow validator and the agent API to them is the next step.
