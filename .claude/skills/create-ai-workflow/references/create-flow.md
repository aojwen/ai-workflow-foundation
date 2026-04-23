# Guided Create Flow

Use this flow whenever the user wants to create a new workflow.

## Goal

Collect only the information needed to create a usable first version of the workflow, then pause for explicit user confirmation before any files are created.

The created workflow MUST encode an **Admission Control orchestration model**:

- One main agent orchestrates (pure executor, DOES NOT compute routing)
- Sub-agents execute steps and emit `nextSteps` signals
- Routing logic is strictly maintained in `routing.json` (DAG-based admission control)

## Conversation structure

Run creation in four phases.

### Phase 1: Orient

State that you are going to:

- clarify the workflow goal and identity
- identify major steps and their admission conditions
- define step inputs, outputs, and routing rules
- confirm the plan with the user
- create the workflow scaffold after explicit approval

Keep this brief.

### Phase 2: Guided questions

Ask the minimal set of questions needed to create a solid first draft. **You MUST clarify all necessary details before proceeding.**

Preferred question order:

1. **Goal**: What should this workflow accomplish from start to finish?
2. **Workflow ID**: What name should we use for the workflow ID (slug format)?
3. **Steps**: What are the major steps in sequence?
4. **For each step**:
   - What is the specific task/purpose?
   - What inputs does it require? (including `workDir`)
   - What outputs does it write? (must be globally unique)
   - What `nextSteps` signals should it emit?
5. **Routing Conditions** (for each step after the first):
   - Which upstream steps must complete first? (`depends_on`)
   - What output values must match? (`required_inputs` - supports `regex:...` for fuzzy matching)
   - Are there alternative paths? (multiple condition sets = OR logic)
6. **Storage**: Should it use the default location `.ai-workflows/<workflow-id>/`, or a custom directory?
7. **Test Cases**: What are example inputs and expected results for a "happy path" test case?

## Questioning Rules

- Ask grouped questions, but ensure **discovery** is complete.
- Do not initialize the workflow until you have a clear understanding of every step's role.
- **If routing logic is undefined or the user is unsure, default to linear sequential routing:**
  - Entry step: `depends_on: []`, `required_inputs: {}`
  - Subsequent steps: `depends_on: [previous_step]`, `required_inputs: { "previous_step.success": true }`
- Propose one "happy-path" test case per step as part of the discovery.

### Phase 3: Confirmation summary

Before creating anything, present a compact summary using the format in `../templates/confirmation-summary.template.md`.

The confirmation MUST include:

- workflow_id
- goal
- target_dir
- **Routing Strategy**: Admission Control via `routing.json` (DAG with OR/AND logic)
- **Detailed step list** (Purpose, Admission Conditions, Inputs, Outputs, nextSteps)
- **Test Case structure** (Markdown fixtures: prompt.md, expected.md, assertions.md)

End with a direct approval gate such as:

`Reply with "确认创建" if this plan looks right, and I'll generate it.`

### Phase 4: Create

Only after explicit approval:

1. Write a spec matching `../templates/workflow-spec.template.json` (includes `routing_conditions` for each step)
2. Run `python scripts/create_workflow.py --spec-file <file> --confirm`
3. Report the created workflow directory and explain the fixture structure.

## New Fixture Structure

The workflow will use Markdown-based fixtures for debugging:
`fixtures/<step-id>/<test-case>/`
  - `prompt.md`: Direct sub-agent input (supports `{workDir}` placeholder).
  - `expected.md`: Descriptive expectation.
  - `assertions.md`: Human-readable criteria for main agent validation.

## Good defaults

If the user is unsure, default to:

- **Storage**: `.ai-workflows/<workflow-id>/`
- **Routing**: Linear sequential (each step depends on the previous)
- **Validation**: `presence` for inputs and `semantic_rule` for outputs
- **Fixtures**: one happy-path fixture per step
- **Orchestration Model**: Admission Control (main agent routes via `routing.json`, sub-agents execute)

## Anti-patterns

Do not:

- create files before approval
- ask the user to run scripts themselves
- ask ten small serial questions when three grouped questions would do
- force strict JSON validation on steps that naturally output markdown or prose
- forget to define `routing_conditions` for each step (defaults to linear if omitted)

## Admission Control Model Reference

The workflow uses **Admission Control** routing:

```
┌─────────────────┐     ┌───────────────────────┐     ┌──────────────┐
│   Main Agent    │────▶│  Admission Control    │────▶│ routing.json │
│ (pure executor) │     │  (run_workflow.py)    │     │   (DAG)      │
└─────────────────┘     └───────────────────────┘     └──────────────┘
                               ▲
                               │
                        ┌──────────────┐
                        │  Sub-Agents  │
                        │ (emit signals│
                        │  nextSteps)  │
                        └──────────────┘
```

Key rules:
- **Scoped Evaluation**: Only evaluate condition sets where the newly completed step is in `depends_on`
- **OR Logic**: Multiple condition sets = any can trigger
- **AND Logic**: Within a set = all `depends_on` + all `required_inputs` must satisfy
- **Re-entry Guard**: A step cannot activate if already running
- **Regex Matching**: `"regex:^pattern"` for fuzzy input validation
- **Fail Fast**: Dependencies met but inputs mismatch = immediate failure
