---
name: execute-ai-workflow
description: Orchestration and execution of isolated, step-based AI workflows. Use this skill to run a workflow, manage state transitions, and delegate step execution to sub-agents.
---

# Execute AI Workflow

Use this skill to run a previously created AI workflow. This skill enforces a strict separation between orchestration (main agent) and execution (sub-agents).

## Design Principles

- **Main Agent Orchestration:** The main agent owns the routing logic, selects the next step, prepares handoff packets, and updates the run state.
- **Sub-Agent Execution:** Every workflow step MUST be executed by a sub-agent. The main agent must not perform the business logic of a step.
- **State Management:** Progress is recorded in a per-run state file (`runs/<workflow-id>/<run-id>/state.json`).
- **Resumability:** This skill supports resuming a workflow from the last successful step by providing the `workflow_id` and `run_id`.

## When to use

- You need to execute an AI workflow end-to-end.
- You want to resume a paused or failed workflow using its `run_id`.
- You need to manage complex routing and branching in an agentic process.

## Execution & Logging Workflow

1. **Initialization / Resume:**
   - Resolve the workflow from `.ai-workflows/<workflow-id>/`.
   - If a `run_id` is provided, load the existing state from `runs/<workflow-id>/<run-id>/state.json`.
   - If no `run_id` is provided, create a new run directory and state file.
2. **Step Selection:** Decide the next step based on the routing table in `orchestration.md` and the current run state.
3. **Execution Logging (Pre-step):**
   - Save the full prompt intended for the sub-agent to `runs/<workflow-id>/<run-id>/<step-id>/prompt.md`.
4. **Delegation:** Invoke a sub-agent to execute the step.
5. **Execution Logging (Post-step):**
   - Save the raw response from the sub-agent to `runs/<workflow-id>/<run-id>/<step-id>/response.md`.
6. **Validation & State Update:**
   - Validate the output against the step's assertions.
   - Update `runs/<workflow-id>/<run-id>/state.json` with the result.
   - Decide the next action.

## Directory Structure (Project Root)

```text
runs/
  <workflow-id>/
    <run-id>/
      state.json            # Overall run status and state
      <step-01-id>/
        prompt.md           # Full prompt sent to sub-agent
        response.md         # Full response from sub-agent
        <other-files>       # Any artifacts produced by this step default here
      <step-02-id>/
        ...
```
