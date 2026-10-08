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

## An engine in one file

You do not need a `capability.yaml` for your own code. A Python file with a `CAPABILITY` (or `CAPABILITIES`) literal is an engine. The whole system is then two files: the engine and the workflow. See [examples/single_file](../examples/single_file).

```python
# engine.py
from pathlib import Path

CAPABILITY = {
    "id": "my.word_count",
    "description": "Counts the words in a text file.",
    "network": False,
    "writes_external_state": False,
}

def word_count(source: Path) -> int:
    return len(source.read_text().split())
```

- Inputs come from the parameters: the annotation is the type (`str`, `int`, `float`, `bool`, `list`, `dict`, `Path` for a file, `Literal["a", "b"]` for a choice), and a default makes the input optional.
- The output is the return annotation, named `result`. Return a dict and list `"outputs"` for several.
- Optional keys: `title`, `version`, `status`, `function`, `env`, `binaries`, `packages`, `hardware`, `estimate_usd`, `failure_modes`, or full `inputs` and `outputs` to override what is derived.
- **Leave out `network` or `writes_external_state` and the factory assumes the risky answer** (network yes, writes externally yes, so approval is required). Say `False` when it is true.
- The file is read as text and is never executed when the factory loads it, so adding a source cannot run anyone's code. It only runs when a workflow that uses it runs.
- Several files with the same name (`engine.py`) in different folders are fine.

## Look before you run

```bash
python -m studio describe story.video.generate     # what it takes, gives, needs and may do
python -m studio plan workflow.yaml --sources ./my_tools   # what running it would involve; runs nothing
```

`plan` lists the steps in the order they would run, which need approval, the cost it can add up and for which steps it is unknown, and whether **this machine** has what the steps need (environment variables, programs, Python packages). It exits with 0 when ready, 3 when something is missing and 1 when the workflow is not valid; `--json` gives the same thing for other programs.

## Starting files

```bash
python -m studio new engine my_tools/summarize.py --id team.summarize
python -m studio new workflow flow.yaml --id my_flow --use team.word_count team.headline --sources my_tools
```

`new engine` writes a valid single-file engine to edit. `new workflow` writes a workflow that runs the capabilities you name in order, wiring an input to an earlier output only when the choice is unambiguous (same name, or the only output of that type); everything else becomes a workflow input, and it prints what it connected. Neither command overwrites an existing file.

## Where capabilities come from

Anywhere you say. A source is a directory (searched for `capability.yaml` files and single-file engines) or a single file, and you can combine as many as you like:

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
- It checks required environment variables, programs and Python packages (`requires.packages`) for every step **before** starting, so a missing library stops the run before anything costly has happened. Python engines run in the same Python as the runner, so the package must be installed there. A command-line engine is checked with the Python its command uses.
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
