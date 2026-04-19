# Step Template

```md
---
step_id: <step-id>
title: <human readable title>
purpose: <what this step does>
inputs_required:
  - <input-a>
optional_inputs:
  - <input-b>
outputs_written:
  - <output-a>
side_effects:
  - writes runs/<run-id>/artifacts/<file>
recommended_next_step: <step-id-or-stop>
---

# Step Instructions

## Intended Executor

This step is intended to be executed by a child agent.
The main agent may orchestrate, inspect, validate, and persist state, but should not directly perform this step's business work except under an explicit exception recorded in run state.
This step should normally be executed only after the main agent prepares a handoff packet for it.

## Machine Contract

```json
{
  "step_id": "<step-id>",
  "inputs_required": ["<input-a>"],
  "outputs_written": ["<output-a>"],
  "validation": {
    "input": [
      {
        "kind": "presence",
        "target": "<input-a>"
      }
    ],
    "output": [
      {
        "kind": "semantic_rule",
        "target": "<output-a>",
        "rule": "Describe what makes this output acceptable."
      }
    ],
    "side_effects": []
  },
  "recommended_next_step": "<step-id-or-stop>"
}
```

## Scope

Work only on this step. Do not decide final routing. Do not load future step files unless the orchestrator explicitly asks for them.

## Input Contract

- Required:
  - `<input-a>` must exist and be readable
- Optional:
  - `<input-b>` may refine the output

## Output Contract

Produce:

- `<output-a>`

Write outputs in a form that the orchestrator can store under `step_outputs.<step_id>`.

## Completion Checks

- The required inputs were used
- The output is complete enough for the next routed step
- Any side effects were recorded

## Failure Handling

If required inputs are missing or contradictory:

- stop this step
- explain the missing dependency
- emit a small failure object for the orchestrator

## Recommended Debug Fixture

- fixture path: `fixtures/<step-id>/input.json`
- expected output path: `fixtures/<step-id>/expected-output.md`
- optional replay snapshot path: `snapshots/<step-id>/<snapshot-name>/state-before.json`
```
