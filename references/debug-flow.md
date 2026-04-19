# Debug Flow

Use this flow when the user wants to debug a workflow or a single step.

## Core rule

Debugging is still orchestrated by the main agent.

That means the main agent:

- selects the target step
- chooses the fixture or snapshot
- determines what is being tested
- compares observed vs expected behavior
- decides whether the main workflow state should remain untouched

## Debug modes

### 1. Fixture debug

Use curated inputs from `fixtures/<step-id>/`.

Best for:

- developing a step the first time
- regression checks
- stable repeatable tests

### 2. Snapshot replay

Use captured inputs and pre-step state from `snapshots/<step-id>/<snapshot-name>/`.

Best for:

- reproducing a real failure
- replaying a messy edge case
- investigating route decisions in context

## Standard debug loop

1. Main agent identifies the target step.
2. Main agent loads the step file.
3. Main agent selects a fixture or snapshot.
4. Main agent delegates that step to a child agent unless the debug task is purely structural inspection.
5. Main agent validates the observed output against:
   - structural expectations
   - semantic expectations
   - expected side effects
6. Main agent records:
   - observed output
   - expected output
   - mismatch
   - likely cause
   - proposed fix
7. Main agent decides whether to:
   - rerun the step
   - patch the step
   - update the fixture
   - apply the result back to the real run

## Isolation rules

- debug runs should write into isolated debug directories or snapshots
- the main run state should remain unchanged by default
- the user must opt in before a debug result is promoted back into the main run

## Helper scripts

Helper scripts are acceptable for:

- preparing a debug session
- creating snapshot folders
- writing normalized debug reports
- serving a local dashboard for viewing and triggering debug runs

They are not the authority for:

- deciding whether a debug run passed
- deciding whether the workflow should continue
- deciding what route the workflow should take next

## Debug dashboard

You may use `scripts/debug_dashboard.py` to:

- inspect debug sessions across workflows
- see whether reports or observed outputs exist
- trigger a new `debug-step` session from a browser UI

This dashboard is a visibility and launch surface only. It does not replace main-agent orchestration.
