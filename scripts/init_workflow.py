#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


ORCHESTRATION_TEMPLATE = """---
workflow_id: {workflow_id}
goal: {goal}
entry_step: {entry_step}
run_state_file: runs/<run-id>/state.json
event_log_file: runs/<run-id>/events.ndjson
---

# Orchestration

## Main Agent Responsibilities

- Read this file first and treat it as the routing authority
- Decide which step should run now
- Prepare a step handoff packet
- Trigger normal step execution in a sub-agent
- Validate the returned output based on step assertions
- Update run state
- Decide whether to continue, branch, retry, or stop
- Record why each route decision was made
- Never do normal step business work directly

## Sub-Agent Responsibilities

- Load only the assigned step
- Treat the received handoff packet as the full execution boundary
- Return the step result in the declared contract shape
- Never decide global workflow routing

## Machine Contract

```json
{{
  "workflow_id": "{workflow_id}",
  "entry_step": "{entry_step}",
  "routes": {routes_json}
}}
```

## Route Table

| Condition | Next step |
| --- | --- |
| new run | {entry_step} |
| current step completes | see machine contract routes |
"""


STEP_TEMPLATE = """---
step_id: {step_id}
title: {title}
purpose: {purpose}
inputs_required:
{inputs_yaml}
outputs_written:
{outputs_yaml}
recommended_next_step: {recommended_next}
---

# Step Instructions

## Intended Executor

This step is intended to be executed by a sub-agent.
The main agent may orchestrate, inspect, validate, and persist state, but should not directly perform this step's business work.

## Machine Contract

```json
{machine_contract_json}
```

## Input Contract

- Required inputs must be present in the handoff packet.

## Output Contract

Produce the declared outputs. The main agent will validate these against the step's assertions.

## Completion Checks

- All required inputs were utilized.
- Outputs match the descriptive expectations and assertions defined in the test fixtures.
"""


RUN_STATE_TEMPLATE = """{{
  "run_id": "",
  "workflow_id": "{workflow_id}",
  "status": "ready",
  "current_step": "{entry_step}",
  "completed_steps": [],
  "step_outputs": {{}},
  "route_decision": {{
    "chosen_next_step": "{entry_step}",
    "reason": "new run",
    "decided_by": "main-agent",
    "timestamp": ""
  }},
  "blockers": [],
  "retry_state": {{
    "step_id": null,
    "attempt_count": 0,
    "last_failure_reason": null
  }},
  "artifacts": [],
  "created_at": "",
  "updated_at": ""
}}
"""

FIXTURE_PROMPT_TEMPLATE = """# Test Prompt: {step_id} - {test_case}

## Goal
{purpose}

## Inputs
{inputs_json}

## Instructions
Please execute the step `{step_id}` with the provided inputs.
"""

FIXTURE_EXPECTED_TEMPLATE = """# Expected Output: {step_id} - {test_case}

## Summary
{expected_summary}

## Details
- [ ] Output contains {first_output}
- [ ] Output is formatted as requested
"""

FIXTURE_ASSERTIONS_TEMPLATE = """# Assertions: {step_id} - {test_case}

The main agent should use these criteria to judge the success of the sub-agent's execution:

1. **Completeness**: All declared outputs are present.
2. **Relevance**: The output directly addresses the step's purpose: {purpose}.
3. **Accuracy**: {expected_summary}
4. **Constraints**: No unrelated files were modified and global routing was not attempted.
"""


def slugify(text: str) -> str:
    value = text.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in value:
        value = value.replace("--", "-")
    return value.strip("-")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
      path.write_text(content, encoding="utf-8")


def build_workflow_root(project_root: str, workflow_id: str, target_dir: str | None = None) -> Path:
    base = Path(project_root).expanduser().resolve()
    return Path(target_dir).expanduser().resolve() if target_dir else base / ".ai-workflows" / workflow_id


def build_step_id(index: int, name: str) -> str:
    return f"step-{index:02d}-{slugify(name)}"


def default_routes(step_ids: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "from": step_id,
            "when": "always",
            "next_step": step_ids[index + 1] if index + 1 < len(step_ids) else "STOP",
            "reason": "default linear route",
        }
        for index, step_id in enumerate(step_ids)
    ]


def scaffold_workflow(
    *,
    project_root: str,
    workflow_id: str,
    goal: str,
    steps: list[dict[str, Any]],
    target_dir: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path:
    workflow_id = slugify(workflow_id)
    root = build_workflow_root(project_root, workflow_id, target_dir)
    raw_step_names = [step["name"].strip() for step in steps if step["name"].strip()]
    if not raw_step_names:
        raise ValueError("At least one step is required.")
    step_ids = [build_step_id(index, name) for index, name in enumerate(raw_step_names, start=1)]
    entry_step = step_ids[0]
    routes = default_routes(step_ids)

    write(
        root / "orchestration.md",
        ORCHESTRATION_TEMPLATE.format(
            workflow_id=workflow_id,
            goal=goal,
            entry_step=entry_step,
            routes_json=json.dumps(routes, indent=2),
        ),
    )

    for index, step_id in enumerate(step_ids):
        step_spec = steps[index]
        title = raw_step_names[index].strip().title()
        recommended_next = step_ids[index + 1] if index + 1 < len(step_ids) else "STOP"
        inputs = step_spec.get("inputs_required") or ["TODO"]
        outputs = step_spec.get("outputs_written") or ["TODO"]
        
        step_machine_contract = {
            "step_id": step_id,
            "inputs_required": inputs,
            "outputs_written": outputs,
            "recommended_next_step": recommended_next,
        }
        write(
            root / "steps" / f"{step_id}.md",
            STEP_TEMPLATE.format(
                step_id=step_id,
                title=title,
                recommended_next=recommended_next,
                machine_contract_json=json.dumps(step_machine_contract, indent=2, ensure_ascii=False),
                purpose=step_spec.get("purpose", "TODO"),
                inputs_yaml="\n".join(f"  - {item}" for item in inputs),
                outputs_yaml="\n".join(f"  - {item}" for item in outputs),
            ),
        )
        
        # New fixture structure: fixtures/<step-id>/happy-path/
        test_case = "happy-path"
        fixture_dir = root / "fixtures" / step_id / test_case
        
        fixture_input = step_spec.get("fixture_input") or {f"input_{i}": "TODO" for i in range(len(inputs))}
        fixture_expected = step_spec.get("expected_output_summary") or "A successful execution of the step."
        
        write(
            fixture_dir / "prompt.md",
            FIXTURE_PROMPT_TEMPLATE.format(
                step_id=step_id,
                test_case=test_case,
                purpose=step_spec.get("purpose", "TODO"),
                inputs_json=json.dumps(fixture_input, indent=2, ensure_ascii=False)
            )
        )
        write(
            fixture_dir / "expected.md",
            FIXTURE_EXPECTED_TEMPLATE.format(
                step_id=step_id,
                test_case=test_case,
                expected_summary=fixture_expected,
                first_output=outputs[0] if outputs else "result"
            )
        )
        write(
            fixture_dir / "assertions.md",
            FIXTURE_ASSERTIONS_TEMPLATE.format(
                step_id=step_id,
                test_case=test_case,
                purpose=step_spec.get("purpose", "TODO"),
                expected_summary=fixture_expected
            )
        )

    write(root / "runs" / ".gitkeep", "")
    write(root / "snapshots" / ".gitkeep", "")
    write(
        root / "runs" / "state.example.json",
        RUN_STATE_TEMPLATE.format(workflow_id=workflow_id, entry_step=entry_step),
    )
    write(
        root / "workflow.spec.json",
        json.dumps(
            {
                "workflow_id": workflow_id,
                "goal": goal,
                "project_root": str(Path(project_root).expanduser().resolve()),
                "target_dir": str(root),
                "orchestration_model": "main-agent-routes-sub-agents-execute",
                "steps": steps,
                "metadata": metadata or {},
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
    )
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold an AI workflow with Markdown fixtures.")
    parser.add_argument("--workflow-id", required=True, help="Workflow identifier")
    parser.add_argument("--goal", default="TODO", help="One sentence workflow goal")
    parser.add_argument("--project-root", default=".", help="Current project root")
    parser.add_argument("--target-dir", help="Optional explicit workflow directory")
    parser.add_argument(
        "--steps",
        default="init,process,complete",
        help="Comma separated step names in order",
    )
    args = parser.parse_args()

    steps = [{"name": s.strip()} for s in args.steps.split(",") if s.strip()]
    root = scaffold_workflow(
        project_root=args.project_root,
        workflow_id=args.workflow_id,
        goal=args.goal,
        steps=steps,
        target_dir=args.target_dir,
    )
    print(root)


if __name__ == "__main__":
    main()
