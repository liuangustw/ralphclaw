# Ralph-Claw Starter

Ralph-Claw is a graph-shaped, state-driven coding loop designed to sit on top of an execution substrate such as OpenClaw. This starter repo packages the design work into a runnable skeleton you can evolve.

## What is included

- JSON schemas for task state, current task, failure summaries, and replan proposals
- A state controller: `scripts/update_state.py`
- Deterministic safety layers:
  - patch scope checking
  - minimal-context extraction
  - verifier runner
  - snapshot / rollback
- Prompt contracts for architect, builder, verifier, replanner
- A sample Python mini-project (`slugify_title`) for smoke testing
- A sample workflow graph: `graphs/coding_loop.yaml`

## Important reality check

This package is intentionally conservative:
- `run_builder.sh` and `run_replanner.sh` contain **placeholder agent calls**
- they are designed so you can swap in OpenClaw, Claude Code, Codex CLI, Gemini CLI, or another runner later
- the stability layer is the main deliverable right now

## Quick start

```bash
python -m pip install pytest jsonschema
chmod +x scripts/*.sh
bash scripts/smoke_test.sh
```

The smoke test uses a mock builder-style change path and deterministic verification to validate the control skeleton before you attach a real model runner.

## Suggested next step

Replace the placeholder sections in:
- `scripts/run_builder.sh`
- `scripts/run_replanner.sh`

with your actual OpenClaw or external agent command.

## Repository layout

```text
app/                sample codebase
tests/              sample tests
state/              machine state
schemas/            JSON schemas
prompts/            agent contracts
scripts/            controller + safety tooling
specs/              product / acceptance specs
graphs/             workflow graph
artifacts/          generated outputs during runs
```
