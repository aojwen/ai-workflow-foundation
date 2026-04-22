---
name: execute-ai-workflow
description: Orchestration and execution of isolated, step-based AI workflows. Use this skill to run a workflow end-to-end, manage state transitions, and delegate step execution to sub-agents.
---

# Execute AI Workflow

Use this skill to run a workflow based on the **Admission Control** model. In this model, the Main Agent is a pure executor, and the routing logic is offloaded to a deterministic Python engine reading a standalone `routing.json` file.

## Design Principles
- **Main Agent as Pure Executor:** The Main Agent reads `active_steps` from the state, spawns sub-agents, and submits results. It **DOES NOT** calculate or decide which step comes next.
- **Admission Control Engine (Deterministic Routing):** 
  - Step completions emit `nextSteps` suggestions to `pending_signals`.
  - The deterministic execution script scans the `routing.json` file (which is hidden from the Main Agent's orchestration prompt).
  - A step is moved from `pending_signals` to `active_steps` if **any** of its condition sets (OR logic) in `routing.json` have all `depends_on` and `required_inputs` (AND logic) satisfied.
- **Contract Enforcement:** If a step's dependencies are met but input values do not match any condition set, the workflow **fails fast** with a contract violation error.
- **Workspace Isolation:** Each step runs in an isolated `runs/<workflow-id>/<run-id>/<step-id>/` with an injected `workDir`.

## Execution Workflow

1. **Initialization:**
   - Call the execution script to create `state.md`. The script identifies the `entry_step` and sets it as the first item in `active_steps`.
2. **Step Execution:**
   - The Main Agent looks at `active_steps`. For each step, it reads the instructions from `.ai-workflows/<workflow-id>/steps/`.
   - It prepares the prompt, injects `workDir`, and spawns a sub-agent.
   - It records exact prompts in `sub-agent-prompt.md`.
3. **Outcome Submission:**
   - Once a sub-agent returns its flat JSON, the Main Agent submits it to the execution script's `submit` command.
   - The script updates `state.md` (recording output, adding to `completed_steps`, and signaling `nextSteps` to `pending_signals`).
4. **Admission Scan (Offloaded Logic):**
   - The execution script automatically scans `routing.json` for `pending_signals`.
   - It updates `active_steps` in the `state.md` frontmatter.
   - If a step meets its `depends_on` but fails its `required_inputs` contract, the script sets the workflow status to `failed`.
5. **Finality:**
   - The Main Agent repeats the loop until `active_steps` is empty.

## Directory Structure
```text
runs/<workflow-id>/<run-id>/
  state.md                # Reactive state machine (Frontmatter) + Results (Body)
  <step-id>/
    sub-agent-prompt.md   # Exact prompt used
    response.json         # Raw output
    <artifacts...>        # Generated files
```
