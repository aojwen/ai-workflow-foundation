---
name: create-ai-workflow
description: Guided creation of isolated, step-based AI workflows. Use this skill to design a new workflow, identify its steps, and scaffold the necessary file structure including Markdown-based test fixtures.
---

# Create AI Workflow

Use this skill to design and scaffold a new AI workflow. This skill follows an **Admission Control** model where steps are triggered based on satisfying specific pre-conditions defined in a DAG-based routing table.

## Design Principles

- **Reactive Orchestration:** The main agent coordinates execution but **DOES NOT** compute routing logic. Every step completion emits `nextSteps` (signals).
- **Admission Control (DAG Routing):** The routing rules are strictly maintained in a standalone `routing.json` file. This hides complex DAG logic from the main agent to prevent hallucination. A python script evaluates this file to trigger steps if:
  1. It has been signaled (is in `pending_signals`).
  2. **OR Logic**: At least one "Condition Set" in its `routing.json` entry is satisfied.
  3. **AND Logic (within a Set)**: All `depends_on` steps are completed AND all `required_inputs` match the expected values in `state.md`.
- **Global Variable Uniqueness:** All output attributes (except framework fields like `success`, `nextSteps`) MUST be globally unique across the entire workflow to prevent state collisions.
- **Strict Step Structure:** Each step prompt follows: Step Goal, Input (including `workDir`), Instructions, Recommend Next Steps (array), Output, Success/Failure Criteria.
- **Markdown State:** `state.md` tracks `active_steps`, `completed_steps`, and `pending_signals` in frontmatter. Results are appended to the body.

## When to use

- You need to create a new AI workflow from scratch.
- You need to support complex branching, parallel execution, or merging (Join) logic.

## Workflow Creation Process

### 1. Discovery
Clarify with the user:
- **Workflow ID & Goal**.
- **Steps & Routing Table**: Define the admission conditions (OR/AND logic) for each step.
- **Step Contracts**: Define inputs, globally unique outputs, and success criteria for each step.

### 2. Confirmation Summary
Present the plan using `templates/confirmation-summary.template.md`. **Explicitly highlight the Admission Control logic and global variable names.**

### 3. Scaffolding
Generate:
- `orchestration.md`: Contains the Main Agent's execution contract (Goal and Entry Step).
- `routing.json`: Contains the complete array-based Condition Sets for DAG admission control.
- `steps/*.md` and `steps/schemas/*.json`.
- `fixtures/` for test-driven development.

## Standard Directory Layout
```text
.ai-workflows/<workflow-id>/
  orchestration.md          # Machine Contract (Entry Step ONLY)
  routing.json              # Admission Control DAG definition
  workflow.spec.json        # Metadata
  steps/
    step-NN-<name>.md       # Instruction sets
    schemas/                # JSON schemas
  fixtures/                 # Markdown-based test cases
```
