# Architecture Notes

This skill follows a structured **Admission Control** orchestration model where routing logic is offloaded to a deterministic Python engine, while a main agent manages workflow state and coordinates sub-agent execution.

## Core Architecture

### Admission Control Model

The routing responsibility is **decoupled** from the main agent:

- **Main Agent**: Pure executor. Reads `active_steps` from state, spawns sub-agents, and submits results. **DOES NOT** calculate routing logic.
- **Admission Control Engine** (`run_workflow.py`): Deterministic Python engine that reads `routing.json` and resolves step transitions.
- **Sub-Agents**: Execute individual steps and emit `nextSteps` signals as suggestions.

### Routing Logic (routing.json)

Routing is strictly maintained in a standalone `routing.json` file. A step is triggered when:

1. **Signal**: The step has been signaled (is in `pending_signals`).
2. **OR Logic**: At least one "Condition Set" in its `routing.json` entry is satisfied.
3. **AND Logic** (within a Set): All `depends_on` steps are completed AND all `required_inputs` match expected values.

```json
{
  "step-02-analysis": [{
    "condition_name": "Standard path",
    "depends_on": ["step-01-intake"],
    "required_inputs": {
      "step-01-intake.success": true
    }
  }, {
    "condition_name": "Alternative path",
    "depends_on": ["step-01-intake"],
    "required_inputs": {
      "step-01-intake.status": "regex:^pass.*"
    }
  }]
}
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Scoped Evaluation** | Only evaluates condition sets where the newly completed step is listed in `depends_on`. Prevents unrelated conditions from causing ambiguous routing. |
| **Re-entry Guard** | A step cannot be activated if it is currently running. Re-entry signals queue in `pending_signals`. |
| **Regex Matching** | Supports fuzzy matching for inputs (e.g., `"regex:^pass.*"`). |
| **Fail Fast** | If dependencies are met but inputs don't match, the workflow fails immediately with a contract violation error. |

---

## State Management: state.md

The run state is maintained in a human-readable `state.md` file.

- **Frontmatter (JSON)**: Tracks reactive state machine state:
  - `active_steps`: Currently executing steps
  - `completed_steps`: Steps that have finished
  - `pending_signals`: Steps waiting for admission
  - `step_outputs`: Output data from completed steps
- **Body (Markdown)**: Records detailed step outcomes for human readability.

---

## Standardized Step Structure

Every step MUST follow this contract:

1. **Step Goal**: Clear task definition.
2. **Input**: Descriptive dynamic context requirements (including mandatory `workDir`).
3. **Instructions**: Detailed business logic and execution rules.
4. **Recommend Next Steps**: Sub-agent emits an **array of step IDs** as suggestions.
5. **Output**: Flat JSON with `success`, `nextSteps`, `schema`, and globally unique business fields.
6. **Success/Failure Criteria**: Clear acceptance standards.

---

## Isolation and Traceability

Each step execution is isolated in its own directory:
`runs/<workflow-id>/<run-id>/<step-id>/`

- `sub-agent-prompt.md`: The exact input used to spawn the executor (mandatory for auditability).
- `response.json`: The raw output from the executor.
- `<artifacts>`: Any files produced during execution.

The main agent records the final outcome in `state.md`, referencing artifact paths for downstream consumption.

---

## Contracts and Schemas

Every step defines a JSON schema for its output. This schema is the source of truth for:

1. **Validation**: Confirming the sub-agent met the contract.
2. **Global Uniqueness**: All output variable names (except `success`, `nextSteps`, `schema`) MUST be globally unique across the entire workflow to prevent state collisions.
