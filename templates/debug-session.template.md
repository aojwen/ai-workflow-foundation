# Debug Session Template

```md
# Debug Recipe: <step-id>

## Goal

Re-run `<step-id>` in isolation and compare observed output against an expected result.

## Inputs

- fixture: `fixtures/<step-id>/input.json`
- optional snapshot: `snapshots/<step-id>/<snapshot-name>/state-before.json`

## Procedure

1. Create an isolated run id such as `debug-2026-04-17T20-00-00Z`.
2. Load only the target step file.
3. Prepare a compact handoff packet for the target step unless the debug task is pure inspection.
4. Delegate the target step to a child agent.
5. Write observed output to `runs/<run-id>/artifacts/<step-id>-observed.md`.
6. Compare against `expected-output.md`.
7. Record mismatch, hypothesis, and next fix.
8. If useful, use `scripts/run_workflow.py debug-step <workflow-dir> --step-id <step-id>` only as a helper to prepare the debug session.

## Report Format

- step id
- fixture used
- expected summary
- observed summary
- mismatch
- probable cause
- proposed patch
```
