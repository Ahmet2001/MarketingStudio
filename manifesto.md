# MarketingStudio Manifesto
### The Workshop for Autonomous Marketing

> This is the Studio's own design statement. The project-wide manifesto, covering the agent, the assets, the Studio and the pool together, is in [MarketingPool/manifesto.md](https://github.com/Ahmet2001/MarketingPool/blob/main/manifesto.md).

## 1. Vision

MarketingStudio is not just a content creation platform, a workflow editor, or an automation dashboard.

**MarketingStudio is a workflow factory: it turns marketing capabilities into new, ready-to-use capabilities.**

Today, humans design marketing workflows. They select tools, configure operations, establish execution sequences, and define the conditions under which automation runs.

In the future, intelligent agents will increasingly perform these same activities.

Our goal is to build the environment that serves both worlds.

**Human-built workflows today. Agent-built capabilities tomorrow.**

## 2. The Fundamental Principle

Most marketing operations do not require continuous artificial intelligence reasoning.

They follow repeatable processes:

- Collecting information
- Researching audiences and competitors
- Generating and transforming content
- Preparing marketing assets
- Publishing across platforms
- Monitoring performance
- Analyzing results

These processes can often be represented as deterministic workflows.

Running a known process should not require an agent to rediscover every step.

Instead, intelligence should be used where reasoning, planning, adaptation, and decision-making create meaningful value.

**Reason when necessary. Execute deterministically whenever possible.**

## 3. MarketingStudio as a Workshop

MarketingStudio is the place where marketing operations are assembled into executable systems.

It takes capabilities from wherever they come from, and turns them into workflows that other systems can run.

Capabilities come from any source: engines written for the Studio, tools from the MarketingAssets pool, or anything a person writes. The pool is an open place where people share what they have; the Studio does not depend on it, and a workflow is never tied to it.

A person can write a capability, connect capabilities into a workflow, check it, run it locally to try it, and export it.

Later, the same environment can be opened to intelligent agents, so that an agent is not limited to tools developers have already assembled. That is future work (see section 9) and nothing in today's design depends on it.

**The Studio transforms available capabilities into new capabilities.**

## 4. Everything Is a Capability

A marketing capability may be a simple API operation, a deterministic function, a content-generation pipeline, an LLM-powered task, a complete workflow, or an agent.

A capability is written either as a contract file (`capability.yaml`) or, for a small engine, as a single Python file whose metadata sits next to the function. Engines should be writable in one or two files.

Every capability should have a discoverable interface describing:

- What it does
- Which inputs it accepts
- Which outputs it produces
- Which resources it requires
- What permissions it needs
- How it can be executed
- What it costs and how failures are handled

This common abstraction makes different technologies composable within the same system.

A workflow is free-form: any shape of steps, with no fixed templates. A workflow created from multiple capabilities can itself become a capability, with its own contract, including file inputs.

This creates a recursive architecture:

**Capabilities form workflows. Workflows become capabilities. Capabilities enable more complex workflows.**

## 5. Human-Native Today, Agent-Native Tomorrow

MarketingStudio begins as a human-operated environment.

People write workflows and engines as plain files and work with them from the command line: validate, plan, describe, run, export. There is no required visual interface; if one is ever built, it will only be a way to write the same files.

The workflow representation is structured and does not depend on any interface. That keeps the door open for agents to use the same system later without imitating human clicks.

Today, a person writes the workflow, exports it, and moves it to the server side, where an agent or worker runs it. An agent that uses the Studio itself, to discover capabilities, compose and register workflows, is future work, and is deliberately not being built yet.

Humans and agents may one day be two creators using the same infrastructure. Only one of them is here today.

## 6. Separation of Creation and Execution

MarketingStudio is responsible for designing, validating, and exporting workflows.

The server side (Marketing Pool's backend runtime, an agent such as BrowserAgent, or a worker) is responsible for running them, usually on a different machine with a different Python setup.

MarketingAssets is an open pool of reusable capabilities people can draw on. It is a source, not a requirement.

The Studio knows none of these consumers. An export is neutral: a self-contained bundle (workflow, contracts, the runner, single-file engines). Small adapters reshape that bundle for one kind of consumer and only write files.

These responsibilities must remain distinct.

The Studio does not need to be running, or even installed, for an exported workflow to execute.

Likewise, an agent does not need to remain active throughout a deterministic pipeline.

This separation reduces costs, improves reliability, and allows each component to evolve independently.

## 7. Workflows as Tools

A workflow should not exist only as an automation attached to a user interface.

Once validated, it should be possible to export, version, reuse, and invoke it as a tool, or run it as an item of a worker.

For example, a workflow that researches a topic, generates a script, creates a video, and prepares a social media post can become a single callable capability.

Today a workflow leaves the Studio as a bundle and can be reshaped by adapters: an agent tool pack, tool definitions for LLM function calling, a job handler for an existing worker, a standalone queue worker, or an MCP server. The same workflow can serve as a tool or as work done by a worker.

An agent can use this capability without manually performing every internal step.

The workflow remains deterministic where possible, while the agent controls higher-level decisions.

This is how increasingly capable agent systems can be built without making every operation agentic.

## 8. Autonomy Through Reusable Infrastructure

Autonomy is not achieved by giving an LLM unrestricted access to every operation.

It emerges from the combination of reliable capabilities, structured execution, contextual reasoning, feedback, and controlled decision-making.

Agents should be able to improve marketing operations over time, but actions with meaningful external consequences must remain subject to explicit authorization and appropriate safeguards.

This is built in: a step that changes something outside the machine, such as publishing, always requires approval. Exports carry that rule with them, and the queue worker enforces it per step. Before a run, the runner states what is missing (keys, programs, packages) instead of failing halfway, and a plan shows the order, the approvals and the known cost.

Each workflow should be observable, testable, recoverable, and measurable.

A successful system does not merely complete tasks. It makes its results understandable and its behavior controllable.

## 9. Evolution

MarketingStudio will evolve through three architectural stages.

**Stage I — Human-Composed Workflows**

Humans assemble workflows from available capabilities and export them. The server side executes them through deterministic workers and agent tools. **This is the stage we are in.**

**Stage II — Agent-Assisted Workflow Development** *(future work, not started)*

Agents help users discover capabilities, generate workflow definitions, troubleshoot failures, recommend improvements, and optimize execution.

**Stage III — Agent-Composed Marketing Systems** *(future work, not started)*

Agents increasingly design and maintain their own workflows, using MarketingStudio programmatically and turning successful workflows into reusable tools.

The human role transitions from manually constructing each operation toward defining objectives, constraints, budgets, and approval policies.

These stages are a direction of development, not a claim that full agent autonomy is already reliable or available. Nothing in Stage I is built for Stage II and III; it is only kept compatible with them.

## 10. Our Commitment

We are not building another isolated marketing automation application.

We are building the factory in which marketing automation systems are made.

We believe the future of marketing will be shaped by intelligent agents operating through reliable, reusable, and composable tools.

Our architecture must support today's deterministic workflows without limiting tomorrow's autonomous agents.

**MarketingStudio is where marketing capabilities are composed and exported.**

**MarketingAssets is an open pool where capabilities are shared.**

**BrowserAgent is where intelligent reasoning and agent execution enter the system.**

**Marketing Pool is the infrastructure that runs what the Studio exports.**

*Build once. Compose endlessly. Automate intelligently.*