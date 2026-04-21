---
name: execute-ai-workflow
description: Orchestration and execution of isolated, step-based AI workflows. Use this skill to run a workflow end-to-end, manage state transitions, and delegate step execution to sub-agents.
---

# Execute AI Workflow

Use this skill to run a previously created AI workflow. This skill enforces a strict separation between orchestration (main agent) and execution (sub-agents).

## Design Principles
- **No Templates/References**: This skill reads the routing rules directly from the specific workflow's `.ai-workflows/<workflow-id>/orchestration.md` and `steps/`.
- **Main Agent Orchestration:** The main agent owns routing logic, prepares inputs, and updates run state.
- **Sub-Agent Execution:** Every workflow step MUST be executed by a sub-agent. The sub-agent performs the `Instructions`, evaluates its `Success/Failure Criteria`, and returns a flat JSON output.
- **Isolated Runs Directory:** Execution state and artifacts are stored in `runs/<workflow-id>/<run-id>/` at the **Project Root**, completely separate from the workflow definition folder.

## Execution Workflow

1. **Initialization / Resume:**
   - Resolve the workflow definition in `.ai-workflows/<workflow-id>/`.
   - Ensure the execution directory exists: `runs/<workflow-id>/<run-id>/`.
   - If starting fresh, initialize `runs/<workflow-id>/<run-id>/state.md` with frontmatter for progress and a body for step outcomes.
2. **Step Selection & Routing:**
   - Look at the previous step's outcome in `state.md`.
   - **Crucial:** If `success == false`, default to STOP immediately (unless `orchestration.md` specifies retry logic).
   - If `success == true`, route to the `nextStep` indicated in the previous outcome.
3. **Delegation (Handoff) with Workspace Injection:**
   - Read the target step's `.md` file in `.ai-workflows/<workflow-id>/steps/`.
   - Extract required `Input` values from previous outcomes in `state.md`.
   - **CRITICAL**: You MUST inject a Workspace Instruction into the final prompt. Tell the sub-agent: *"Save all generated files, artifacts, and complex data structures to the absolute path: `runs/<workflow-id>/<run-id>/<step-id>/`"*.
   - Spawn a sub-agent using this composite prompt. Save the exact prompt used to `runs/<workflow-id>/<run-id>/<step-id>/sub-agent-prompt.md`.
4. **Outcome Recording:**
   - Save the raw response to `runs/.../<step-id>/response.json`.
   - Verify the JSON structure against `.ai-workflows/<workflow-id>/steps/schemas/<step-id>.schema.json`.
   - Append the result to the body of `state.md`, listing `success`, `nextStep`, and other fields with their descriptions.
5. **Repeat:** Loop until completion or a `success == false` termination.

## Directory Structure
```text
(Project Root)
├── .ai-workflows/
│   └── <workflow-id>/
│       ├── orchestration.md
│       ├── steps/
│       └── workflow.spec.json
│
└── runs/                     <-- ALL execution state lives here
    └── <workflow-id>/
        └── <run-id>/
            ├── state.md
            ├── <step-01-id>/
            │   ├── sub-agent-prompt.md
            │   ├── response.json
            │   └── <artifacts...>
            └── <step-02-id>/...
```
