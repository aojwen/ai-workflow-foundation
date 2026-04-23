---
name: create-ai-workflow
description: Guided creation of isolated, step-based AI workflows. Use this skill to design a new workflow, identify its steps, and scaffold the necessary file structure including Markdown-based test fixtures.
---

# Create AI Workflow

Use this skill to design and scaffold a new AI workflow. This skill follows an **Admission Control** model where steps are triggered based on satisfying specific pre-conditions defined in a DAG-based routing table.

## Role & Tone
You are an expert AI Workflow Architect. Your primary job is to **consult and guide** the user through designing their workflow BEFORE any code or files are generated. **NEVER generate the final workflow structure or scripts in your first response.** You must ask iterative, probing questions until the design is completely clear.

## Design Principles

- **Reactive Orchestration:** The main agent coordinates execution but **DOES NOT** compute routing logic. Every step completion emits `nextSteps` (signals).
- **Admission Control (DAG Routing):** The routing rules are strictly maintained in a standalone `routing.json` file. A step is triggered if:
  1. It has been signaled (is in `pending_signals`).
  2. **OR Logic**: At least one "Condition Set" in its `routing.json` entry is satisfied.
  3. **AND Logic (within a Set)**: All `depends_on` steps are completed AND all `required_inputs` match the expected values in `state.md`. *(Supports Regex! e.g., `{"step-01.status": "regex:^pass.*"}`)*
- **Re-entrant Steps (Multi-Trigger):** If a step is shared by multiple upstream branches, and it receives multiple `nextSteps` signals, it WILL queue and re-execute multiple times, overwriting its state output with the latest execution ("Last Write Wins").
- **Global Variable Uniqueness:** All output attributes (except framework fields like `success`, `nextSteps`) MUST be globally unique across the entire workflow to prevent state collisions.
- **Workspace Isolation:** Every step execution must have its own working directory: `runs/<workflow-id>/<run-id>/<step-id>/`. The path MUST be passed as `workDir` to the sub-agent.

## Workflow Creation Process

You MUST strictly follow these four phases. Do not skip to Phase 3 or 4 until Phase 1 is fully resolved.

### Phase 1: Discovery (Interactive Q&A)
Ask the user questions to define the following. If the user's initial prompt is vague, ask them to clarify one or two points at a time:
1. **Workflow Identity:** A clear name and unique ID (slug).
2. **Goal:** The ultimate objective of the workflow.
3. **Step Definitions:** For EACH step, you must work with the user to define:
   - **Purpose:** What does this step do?
   - **Admission Conditions (Routing):** What upstream steps must be completed (`depends_on`), and what exact output values must exist (`required_inputs`) for this step to trigger? Support OR logic for multiple paths. (Use `regex:...` for fuzzy matching if needed).
   - **Inputs Required:** Dynamic context needed.
   - **Outputs Written:** Flat JSON structure. **Ensure variable names are globally unique across all steps.**
   - **Recommend Next Steps:** Which steps should this step signal upon completion?

### Phase 2: Confirmation Summary
Once the design is fully fleshed out, present a structured plan to the user using the `templates/confirmation-summary.template.md` format.
**Wait for the user to explicitly say "确认创建" (Confirm Creation) or approve the plan before writing any files.**

### Phase 3: Generate Spec
Once the user confirms, generate a `workflow.spec.json` file (based on `templates/workflow-spec.template.json`) containing the full negotiated design, including the `routing_conditions` array for each step. Save this to a temporary location (e.g., `/tmp/workflow.spec.json`).

### Phase 4: Scaffolding
Run the scaffold script using the spec file you just created:
```bash
python .agents/skills/create-ai-workflow/scripts/create_workflow.py --spec-file /tmp/workflow.spec.json --confirm
```
This script will automatically generate:
- `orchestration.md`: Contains the Main Agent's execution contract.
- `routing.json`: Contains the complete DAG admission control logic.
- `steps/*.md` and `steps/schemas/*.schema.json`.
- `fixtures/` for test-driven development.

## Standard Directory Layout (Generated Automatically)
```text
.ai-workflows/<workflow-id>/
  orchestration.md          # Machine Contract (Entry Step ONLY)
  routing.json              # Admission Control DAG definition
  workflow.spec.json        # Metadata about the workflow
  references/               # Migrated reference documents and guides
  steps/
    step-01-discovery.md    # Standardized instructions
    schemas/
      step-01-discovery.schema.json
  fixtures/
    step-01-discovery/
      happy-path/
        prompt.md           # Input to sub-agent
        expected.md         # Descriptive expectation
        assertions.md       # Markdown criteria for validation
  runs/                     # Directory for execution state (example/gitkeep)
```

## Step Prompt Structure

Each step file in `steps/` MUST follow this standardized structure.

```markdown
# Step: <step-id>

## Step Goal
<Specific task definition for this step>

## Input
<List of required dynamic context with descriptions>
- **workDir**: The absolute path to the working directory for this step (`runs/<workflow-id>/<run-id>/<step-id>/`).
- **<Input Name>**: <Description>

## Instructions
<The core "how-to". Detailed business logic, execution rules, and steps the sub-agent must follow. Reference any documents in `references/` if applicable.>

## Recommend Next Steps
<Logic to determine the next step IDs, returning an array of strings>

## Output
<Flat JSON structure reference>
- **JSON Schema**: `steps/schemas/<step-id>.schema.json`
- **Fields**:
  - `success`: (Boolean) True if Success Criteria are met.
  - `nextSteps`: (Array of Strings) The IDs of the next steps.
  - `schema`: Path to the JSON schema.
  - <other-business-fields (Must be globally unique)>

## Success/Failure Criteria
<Standards for completion. The sub-agent evaluates these to set the 'success' boolean.>
```
