# Architecture Notes

This skill follows a structured orchestration model where a main agent manages the workflow's state and transitions, while specialized sub-agents execute individual steps.

## State Management: state.md

The run state is maintained in a human-readable `state.md` file rather than a complex JSON.

- **Frontmatter (YAML)**: Tracks high-level progress (current step, status, completion list).
- **Body (Markdown)**: Records detailed step outcomes. Each outcome includes the field name, its value, and a description (derived from the step's JSON schema) to ensure the agent and user understand the significance of each data point.

## Standardized Step Structure

Every step MUST follow this contract:

1. **Step Goal**: Clear task definition.
2. **Input**: Descriptive dynamic context requirements.
3. **Recommend Next Step**: Sub-agent's logic for the next transition.
4. **Output**: Flat JSON with `nextStep` and `schema` reference.
5. **Success/Failure Criteria**: Clear acceptance standards.

## Routing Model

Responsibility for routing is shared:

- **Sub-Agent**: Calculates the `nextStep` based on the step's logic and internal indicators. It returns this suggestion as part of its output.
- **Main Agent**: Reads the `nextStep` from the sub-agent's output. It **authorizes** this transition by updating `state.md` and preparing the next step's handoff. The main agent retains the flexibility to override the suggestion if the global `orchestration.md` logic dictates otherwise.

This approach reduces the main agent's cognitive load by delegating complex branching logic to the step level while maintaining centralized control.

## Isolation and Traceability

Each step execution is isolated in its own directory under the run:
`runs/<run-id>/<step-id>/`
- `sub-agent-prompt.md`: The exact input used to spawn the executor.
- `response.json`: The raw output from the executor.
- `<artifacts>`: Any files produced during execution.

The main agent records the final outcome in `state.md`, referencing the artifact paths for downstream consumption.

## Contracts and Schemas

Every step defines a JSON schema for its output. This schema is the source of truth for:
1. **Validation**: Confirming the sub-agent met the contract.
2. **Context Enrichment**: Providing descriptions for the fields recorded in `state.md`.
