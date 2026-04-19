# Run State Protocol

The run state is the source of truth for the progress and results of a specific workflow execution.

## Core principle

The **main agent is the only authority** for updating the run state. It ensures consistency across steps and handles routing logic.

## Storage Location

Run state files and step logs are stored at the project root:
- State File: `runs/<workflow-id>/<run-id>/state.json`
- Step Logs: `runs/<workflow-id>/<run-id>/<step-id>/` (contains `prompt.md` and `response.md`)

## State Schema

```json
{
  "run_id": "run-20260418-120000",
  "workflow_id": "example-workflow",
  "status": "ready | in_progress | blocked | completed | failed",
  "current_step": "step-02-process",
  "completed_steps": ["step-01-init"],
  "step_outputs": {
    "step-01-init": {
      "result": "Success",
      "data": { ... }
    }
  },
  "route_decision": {
    "chosen_next_step": "step-02-process",
    "reason": "Sequential default",
    "decided_by": "main-agent",
    "timestamp": "2026-04-18T12:05:00Z"
  },
  "blockers": [],
  "artifacts": [],
  "created_at": "2026-04-18T12:00:00Z",
  "updated_at": "2026-04-18T12:05:00Z"
}
```

## Logging Protocol

For each step execution, the main agent MUST:
1. **Pre-execution**: Save the full prompt that will be sent to the sub-agent to `runs/<workflow-id>/<run-id>/<step-id>/prompt.md`.
2. **Post-execution**: Save the raw, unedited response from the sub-agent to `runs/<workflow-id>/<run-id>/<step-id>/response.md`.
3. **Artifacts**: Ensure any files generated during the execution of this step are saved within `runs/<workflow-id>/<run-id>/<step-id>/`, unless the step explicitly requests saving them elsewhere (e.g., to a final build directory).

## Resumability

To resume a workflow:
1. Provide the `workflow_id` and the existing `run_id`.
2. The main agent will load `runs/<workflow-id>/<run-id>/state.json`.
3. Execution will continue from the `current_step` stored in the state.
