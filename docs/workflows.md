# Writing workflows

A workflow is a file you write yourself. There is no fixed set of step kinds, no limit on the number of steps, and no built-in list of what may follow what. It can branch, run steps in parallel, and join them again.

The factory in [studio/](../studio) checks the file against the capabilities you point it at, then exports it as a capability. It does not depend on the Marketing Assets Pool, on any agent, or on this repository's own engines.

## A workflow file

```yaml
spec_version: "0.1"
workflow:
  id: research_then_post          # lowercase, digits, underscores
  name: Research then post
  inputs:                          # whatever you want to ask the caller for
    topic: {type: text, required: true}
  steps:
    - id: research
      capability: my.research      # any capability id from your sources
      with: {q: "{{ inputs.topic }}"}
    - id: post
      capability: my.post
      with: {text: "{{ steps.research.outputs.notes }}"}
  outputs:
    posted: "{{ steps.post.outputs.id }}"
```

- **Steps** can be any number. Order comes from the references between them, plus optional `needs: [step_id]` for a dependency that has no data flowing through it.
- **`with`** gives each input a value: a literal, `"{{ inputs.<name> }}"`, or `"{{ steps.<step>.outputs.<name> }}"`. Text with references embedded (`"Report: {{ steps.a.outputs.draft }}"`) is allowed for text inputs.
- **Parallel branches** are simply steps that do not depend on each other. See [examples/workflows/parallel_videos.yaml](../examples/workflows/parallel_videos.yaml).
- **Types** are checked when a step output feeds an input. `integer` fits `number`, and `enum` and `url` fit `text`, automatically. For anything else, say so where you wire it: `"{{ steps.a.outputs.count | as integer }}"`. Anything can become `text` (a file becomes its path, a list or object its JSON), and `text` can become any other type; whether it really parses is checked when the workflow runs. A file cannot become an integer. Or declare the input type as `any` to skip the check.

## Rules the factory enforces

Only the rules the capabilities themselves state:

1. Every referenced capability, step, input and output exists.
2. Types match, required inputs have a value, and values are valid literals.
3. The steps contain no cycle.
4. A step whose capability writes to the outside world always requires approval, and `approval: none` on it is an error.

## Where capabilities come from

Anywhere you say. A source is a directory (searched for `capability.yaml`) or a single file, and you can combine as many as you like:

```bash
python -m studio capabilities --sources ./my_tools ~/shared_pool ./engines
export STUDIO_CAPABILITY_SOURCES="./my_tools:$HOME/shared_pool"   # same, for every command
```

With no sources, the factory reads this repository. No source is special, and a shared pool is just one more directory. Two sources defining the same id is an error that names both files.

Only add sources you trust: a capability file says how something is run.

## Commands

```bash
python -m studio capabilities [--sources DIR ...]
python -m studio validate workflow.yaml [--sources DIR ...] [--allow-unknown]
python -m studio export workflow.yaml --out DIR [--sources DIR ...] [--allow-unknown]
python -m studio check [--sources DIR ...]
python -m studio run workflow.yaml [--input name=value ...] [--approve STEP ...] [--approve-all] [--workdir DIR]
```

`check` rejects malformed `capability.yaml` files from any source (every problem is listed) and also checks that the files an execution points to exist. Loading a registry always rejects malformed files.

`--allow-unknown` lets a step name a capability that is not in the registry yet, for example one that only exists where the workflow will run. Such a step is not type checked, and is treated as writing to the outside world, so it needs approval.

## Running a workflow

`python -m studio run` is a plain local runner: it executes the steps one at a time in dependency order on this machine.

```bash
python -m studio run workflow.yaml --sources ./my_tools ./engines --input topic="a small town mystery" --workdir ./runs/first
```

- Each step gets its own folder under the workdir, with a `step.log` for command-line capabilities.
- It checks required environment variables and programs for every step **before** starting.
- A step that writes to the outside world is **not run** unless approved: name it with `--approve STEP`, use `--approve-all`, or answer the prompt in a terminal. Without approval the run stops before that step.
- It can execute `cli`, `python` and `workflow` capabilities. `http` capabilities are not supported by the local runner and fail with a clear message.
- A command-line capability's output is the newest file matching its pattern. `exclude` names files or folders to ignore, and `**` searches subfolders.
- No parallelism, retries or queue. It exists so you can run what you wrote; a larger runtime can replace it because the workflow files do not depend on it.

## What export produces

`workflow.yaml` (your workflow with dependencies and approvals filled in) and `capability.yaml` (the workflow as one capability, `workflow.<id>`). The capability's requirements are the union of its steps, it needs approval if any step writes externally, and its cost is the sum or `null` if any step is unmeasured. Because the output is itself a capability, a workflow can be a step in another workflow.

## Storyforge's editor nodes

`apps/studio-api` still stores workflows as the old generator / scheduler / destination nodes. Those are translated into a workflow document for export and run through the same core, so they are a special case of this system, not a different one. New workflows should be written as files.

## Not supported yet

Loops over lists, conditions, and retries are not in the format, and the local runner does not run steps in parallel. Nothing in it prevents adding them; they were left out rather than guessed.
