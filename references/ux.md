# UX Rules

This skill should feel like a productized workflow builder, not a raw script wrapper.

## Creation flow

When the user wants to create a workflow:

1. Ask guided questions to clarify:
   - workflow goal
   - workflow id or name
   - major steps
   - entry conditions
   - key outputs
   - whether default location is acceptable
   - whether any steps need stricter validation
2. Summarize the planned workflow in a compact confirmation block.
3. Wait for explicit user approval.
4. Store the summarized plan as a structured spec.
5. Only after approval, create the workflow automatically.
5. Do not ask the user to run scripts manually if the agent can do it.

## Creation implementation

- Use `templates/workflow-spec.template.json` as the canonical spec shape.
- Use `references/create-flow.md` as the required guided-question flow.
- Use `templates/confirmation-summary.template.md` as the required approval format.
- Use `scripts/render_create_summary.py --spec-file <file>` when helpful to render the approval block consistently.
- Use `scripts/create_workflow.py --spec-file <file>` to print the creation summary.
- Use `scripts/create_workflow.py --spec-file <file> --confirm` only after the user explicitly approves.

## Default storage

- Default workflow root: `.ai-workflows/` under the current project root.
- Default workflow location: `.ai-workflows/<workflow-id>/`
- The user may override the directory.

## Execution flow

When the user wants to run a workflow:

1. Accept `workflow_id` as the primary reference.
2. Resolve it automatically from `.ai-workflows/<workflow-id>/`.
3. Only ask for a directory if the workflow id cannot be found.

## Debug flow

When the user wants to debug a step:

1. Accept `workflow_id` and `step_id`.
2. Resolve the workflow from the default root.
3. Prepare an isolated debug run automatically.
4. Prefer fixtures first, snapshots second.
