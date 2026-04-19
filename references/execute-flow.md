# Execution Flow

Use this flow to run or resume a workflow.

## Core Principle

The **main agent is the orchestrator**, and **sub-agents are the executors**. The main agent manages routing, state, and logging, while sub-agents handle individual step logic.

## Phase 1: Initialization & Resume

1. **Resolve Workflow:** Locate the workflow directory in `.ai-workflows/<workflow-id>/`.
2. **Load Orchestration:** Read `orchestration.md` to understand routing and contracts.
3. **Determine Run State:**
   - **New Run:** If no `run_id` is provided, generate a new one (e.g., `run-20260418-120000`). Create the directory `runs/<workflow-id>/<run-id>/` at the project root. Initialize `state.json` with the `entry_step`.
   - **Resume:** If a `run_id` is provided, load `runs/<workflow-id>/<run-id>/state.json`. Verify that the workflow is not already finished.
4. **Context Loading:** Load the outputs of all completed steps from the `state.json`.

## Phase 2: Execution Loop

1. **Next Step:** Identify the `current_step` from the run state.
2. **Prepare Handoff:**
   - Gather required inputs based on the step's contract and prior outputs.
   - Construct the full prompt for the sub-agent.
3. **Log Prompt (MANDATORY):** Save the full prompt intended for the sub-agent to `runs/<workflow-id>/<run-id>/<step-id>/prompt.md`.
4. **Delegate:** Invoke the sub-agent to execute the step.
5. **Log Response (MANDATORY):** Save the sub-agent's raw response to `runs/<workflow-id>/<run-id>/<step-id>/response.md`.
6. **Artifact Storage:** Any files or artifacts produced by the sub-agent during this step MUST be saved in `runs/<workflow-id>/<run-id>/<step-id>/` unless the step contract explicitly specifies a different destination.
7. **Validate:** The main agent evaluates the response against the step's assertions.
8. **Update State:**
   - Write the step output and updated status to `runs/<workflow-id>/<run-id>/state.json`.
   - Update `completed_steps` and determine the `current_step` based on routing rules.
9. **Loop or Stop:** Repeat until the routing table points to `STOP`.

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

## Phase 3: Finalization

1. Summarize the workflow results to the user.
2. Provide the path to the final artifacts and the run state.
