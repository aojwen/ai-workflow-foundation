# Guided Create Flow

Use this flow whenever the user wants to create a new workflow.

## Goal

Collect only the information needed to create a usable first version of the workflow, then pause for explicit user confirmation before any files are created.

The created workflow must encode an **agent-first orchestration model**:

- one main agent orchestrates
- child agents execute steps
- helper scripts remain optional

## Conversation structure

Run creation in four phases.

### Phase 1: Orient

State that you are going to:

- clarify the workflow goal
- identify major steps
- choose the workflow id and storage location
- confirm the plan
- create it automatically after approval

Keep this brief.

### Phase 2: Guided questions

Ask only the smallest set of questions needed to create a solid first draft. **You MUST clarify all necessary details including step-by-step tasks, inputs, and outputs before proceeding.**

Preferred question order:

1. What should this workflow accomplish from start to finish?
2. What name should we use for the workflow id?
3. What are the major steps in sequence?
4. **For each step, what is the specific task, required inputs, and expected outputs?**
5. **Routing: Do the steps run strictly in order, or are there conditional branches, alternate paths, or loops?**
6. Should it use the default location `.ai-workflows/<workflow-id>/`, or do you want a custom directory?
7. What are some example inputs and expected results for a "happy path" test case?

## Questioning rules

- Ask grouped questions, but ensure **discovery** is complete.
- Do not initialize the workflow until you have a clear understanding of every step's role.
- **If routing logic is undefined or the user is unsure, default to linear sequential routing.**
- Propose one "happy-path" test case per step as part of the discovery.

### Phase 3: Confirmation summary

Before creating anything, present a compact summary using the format in `../templates/confirmation-summary.template.md`.

The confirmation must include:

- workflow id
- goal
- target directory
- **Detailed step list (Task, Input, Output)**
- **Routing Strategy (Sequential or Custom conditions)**
- **Proposed Test Case structure (Markdown fixtures)**
- orchestration model: main agent routes, sub-agents execute

End with a direct approval gate such as:

`Reply with "确认创建" if this plan looks right, and I’ll generate it.`

### Phase 4: Create

Only after explicit approval:

1. Write a spec matching `../templates/workflow-spec.template.json`
2. Run `scripts/create_workflow.py --spec-file <file> --confirm`
3. Report the created workflow directory and explain the fixture structure.

## New Fixture Structure

The workflow will use Markdown-based fixtures for debugging:
`fixtures/<step-id>/<test-case>/`
  - `prompt.md`: Direct sub-agent input.
  - `expected.md`: Descriptive expectation.
  - `assertions.md`: Human-readable criteria for main agent validation.

## Good defaults

If the user is unsure, default to:

- storage: `.ai-workflows/<workflow-id>/`
- route model: linear happy-path scaffold
- validation: `presence` for inputs and `semantic_rule` for outputs
- fixtures: one happy-path fixture per step
- orchestration model: main agent decides next step, child agents run steps

## Anti-patterns

Do not:

- create files before approval
- ask the user to run scripts themselves
- ask ten small serial questions when three grouped questions would do
- force strict JSON validation on steps that naturally output markdown or prose
