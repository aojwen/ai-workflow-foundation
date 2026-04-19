# Architecture Notes

This skill is built around a split between static workflow definition and mutable runtime state.

## Why the BMAD-style pattern is strong

- Loading one step at a time reduces context pollution.
- Linear step files are easy for an agent to follow reliably.
- Step-local instructions make behavior predictable.

## Why direct next-step coupling becomes a problem

When a step both performs work and decides the next step, three concerns get mixed together:

1. business logic
2. routing logic
3. runtime persistence

That makes debug expensive because:

- replay depends on shared global state
- re-running one step may require undoing downstream state
- step behavior is harder to test outside the full chain

## Better split

Use three layers.

### 1. Workflow definition

Mostly static files:

- `orchestration.md`
- `steps/*.md`
- `fixtures/**`

This layer defines contracts and routing rules.

### 2. Runtime state

Per-run mutable files:

- `runs/<run-id>/state.json`
- `runs/<run-id>/events.ndjson`
- `runs/<run-id>/artifacts/*`

This layer records what the **main agent decided and observed** in one execution.

### 3. Snapshots for replay

Reusable debug captures:

- `snapshots/<step-id>/<snapshot-name>/input.json`
- `snapshots/<step-id>/<snapshot-name>/state-before.json`
- `snapshots/<step-id>/<snapshot-name>/expected-output.md`

This layer exists so a step can be replayed without editing the main run.

## Recommended contracts

Each step should expose a contract with these sections:

- `step_id`
- `purpose`
- `inputs_required`
- `optional_inputs`
- `outputs_written`
- `side_effects`
- `completion_checks`
- `recommended_next_step`

The orchestrator should expose:

- workflow goal
- entry step
- route table
- run state schema
- failure handling policy
- debug policy

In this skill, "orchestrator" means the **main agent working from the orchestration file**, not a code runtime.

## Routing model

Preferred routing order:

1. orchestrator route table
2. current run state
3. step output hints

This means a step can suggest `recommended_next_step`, but the orchestrator makes the final decision.

## State model

Avoid one global status file that must be manually rewound.

Prefer this:

```json
{
  "run_id": "run-2026-04-17T20-00-00Z",
  "workflow_id": "example-workflow",
  "current_step": "step-02-collect-context",
  "completed_steps": ["step-01-init"],
  "step_outputs": {
    "step-01-init": {
      "summary": "..."
    }
  },
  "artifacts": [],
  "route_decision": {
    "chosen_next_step": "step-02-collect-context",
    "reason": "entrypoint"
  }
}
```

Key rule:

- The run state is disposable.
- The workflow definition is durable.
- The main agent owns state transitions.

## Debug model

There are two useful debug modes.

### Fixture debug

Use curated, stable inputs for a step.

Best for:

- early development
- regression checks
- reproducing common edge cases

### Snapshot replay

Capture the exact inputs and relevant state before a failed step, then replay from that snapshot.

Best for:

- production-like failures
- routing bugs
- prompt regressions tied to real context

## Minimum viable workflow standard

For a new workflow, require:

- one `orchestration.md`
- at least one step file
- one fixture per step
- one run-state schema
- one debug recipe per step

## Migration advice for an existing BMAD-style workflow

If an existing step currently says "after this, load step X", migrate it like this:

1. keep the business instructions in the step
2. remove mandatory routing ownership from the step
3. add `recommended_next_step`
4. move actual route selection into `orchestration.md` and main-agent reasoning
5. replace shared status mutation with per-run state writes
