# Runtime Contract

This file defines the machine-readable pieces that helper scripts may read and write.

These scripts are optional helpers. They do not outrank the main agent.

## Orchestration contract

Put a `## Machine Contract` section in `orchestration.md` with one JSON code block.

```json
{
  "workflow_id": "example-workflow",
  "entry_step": "step-01-init",
  "routes": [
    {
      "from": "step-01-init",
      "when": "always",
      "next_step": "step-02-process",
      "reason": "linear happy path"
    },
    {
      "from": "step-02-process",
      "when": "output_path_equals",
      "path": "decision.needs_revision",
      "equals": true,
      "next_step": "step-01-init",
      "reason": "loop for revision"
    },
    {
      "from": "step-02-process",
      "when": "output_path_falsey",
      "path": "decision.needs_revision",
      "next_step": "STOP",
      "reason": "workflow complete"
    }
  ]
}
```

Supported route predicates:

- `always`
- `output_path_equals`
- `output_path_truthy`
- `output_path_falsey`

## Step contract

Put a `## Machine Contract` section in each step file with one JSON code block.

```json
{
  "step_id": "step-01-init",
  "inputs_required": ["request"],
  "outputs_written": ["normalized_request"],
  "recommended_next_step": "step-02-process"
}
```

## Helper script commands

Initialize a run state:

```bash
python3 scripts/run_workflow.py start <workflow-id-or-dir> --project-root <project-root>
```

Inspect status:

```bash
python3 scripts/run_workflow.py status <workflow-id-or-dir> --run-id <run-id> --project-root <project-root>
```

Write a normalized step result into helper-managed state:

```bash
python3 scripts/run_workflow.py advance <workflow-id-or-dir> --run-id <run-id> --step-output-file /path/to/output.json --project-root <project-root>
```

Prepare an isolated single-step debug run:

```bash
python3 scripts/run_workflow.py debug-step <workflow-id-or-dir> --step-id step-02-process --project-root <project-root>
```

Capture a replay snapshot:

```bash
python3 scripts/run_workflow.py snapshot-step <workflow-id-or-dir> --run-id <run-id> --step-id step-02-process --name failed-case --project-root <project-root>
```
