# Workflow Orchestration Template

```md
---
workflow_id: <workflow-id>
goal: <one sentence goal>
entry_step: <step-id>
run_state_file: runs/<run-id>/state.json
event_log_file: runs/<run-id>/events.ndjson
---

# Orchestration

## Main Agent Responsibilities

- Read this file first and treat it as the routing authority
- Decide which step should run now
- Prepare a step handoff packet
- Trigger normal step execution in a child agent
- Validate the returned output
- Update run state
- Decide whether to continue, branch, retry, or stop
- Record why each route decision was made
- Record blockers or retry decisions instead of silently guessing
- Never do normal step business work directly

## Child Agent Responsibilities

- Load only the assigned step
- Treat the received handoff packet as the full execution boundary
- Use only the inputs prepared by the main agent
- Return the step result in the declared contract shape
- Never decide global workflow routing
- Never update unrelated workflow files

## Allowed Main Agent Exceptions

- workflow creation and scaffolding
- route decisions
- run-state updates
- snapshot and debug setup
- structural inspection without step execution
- explicit user-approved emergency fallback

## Responsibilities

- Own routing between steps
- Create and update per-run state
- Trigger one step at a time
- Keep step execution and routing separate

## Machine Contract

```json
{
  "workflow_id": "<workflow-id>",
  "entry_step": "<step-id>",
  "routes": [
    {
      "from": "<step-id>",
      "when": "always",
      "next_step": "<next-step-id>",
      "reason": "linear route"
    }
  ]
}
```

## Run State Schema

```json
{
  "run_id": "",
  "workflow_id": "",
  "status": "ready",
  "current_step": "",
  "completed_steps": [],
  "step_outputs": {},
  "route_decision": {
    "chosen_next_step": "",
    "reason": "",
    "decided_by": "main-agent",
    "timestamp": ""
  },
  "blockers": [],
  "retry_state": {
    "step_id": null,
    "attempt_count": 0,
    "last_failure_reason": null
  },
  "artifacts": [],
  "created_at": "",
  "updated_at": ""
}
```

## Route Table

| Condition | Next step |
| --- | --- |
| new run | <step-id> |
| output.<flag> == true | <step-id> |
| output.<flag> == false | <step-id> |
| fatal error | STOP |

## Execution Loop

1. Main agent initializes or loads `runs/<run-id>/state.json`.
2. Main agent resolves `current_step`.
3. Main agent loads only that step file.
4. Main agent prepares a compact step handoff packet from run state, user inputs, fixtures, or snapshots.
5. Main agent delegates the step to a child agent.
6. Child agent executes the step and returns the result.
7. Main agent validates the returned output.
8. Main agent persists outputs under `step_outputs[step_id]`.
9. Main agent evaluates the route table and records a `route_decision`.
10. Main agent updates `current_step`, `status`, and any `blockers` or `retry_state`.
11. Repeat until STOP or completion.

## Debug Policy

- Single-step debug never writes to another run's state.
- Prefer `fixtures/<step-id>/input.json`.
- For failure replay, copy pre-step context into `snapshots/<step-id>/<snapshot-name>/`.
- Debug writes go to `runs/debug-<timestamp>/`.

## Helper Scripts

Optional helper scripts may be used to:

- start a run
- inspect status
- create debug sessions
- capture snapshots

These scripts are not the authority for orchestration decisions.

## Failure Policy

- On step failure, write the observed error and available inputs into the run state.
- Prefer `status: blocked` when a safe next move is unclear.
- Prefer explicit retry bookkeeping over silent overwrites.
- If a normal step was executed by the main agent under an exception, record the exception reason in run state.
- Do not rewrite workflow definition files during execution.
- If routing is ambiguous, stop and surface the ambiguity instead of guessing.
```
