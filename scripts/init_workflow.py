#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any

ORCHESTRATION_TEMPLATE = """# Workflow Orchestration

---
workflow_id: {workflow_id}
goal: {goal}
entry_step: {entry_step}
state_file: runs/{workflow_id}/<run-id>/state.md
---

# Orchestration Logic

## Main Agent Responsibilities
- **Initialization**: Create `state.md` in `runs/{workflow_id}/<run-id>/`.
- **Routing**: Check the `success` field from the previous step. 
  - If `success == true`, route to the `nextStep` provided in the output.
  - If `success == false`, default to STOP (unless custom retry logic is defined).
- **Input Preparation**: Identify inputs for the next step. Gather values from `state.md` or user input.
- **Workspace Injection**: You MUST explicitly tell the sub-agent the directory for this step: `runs/{workflow_id}/<run-id>/{step_id}/`.
- **Sub-Agent Spawning**: Prepare the final prompt (Original Step Prompt + Workspace Instruction) and save it to `runs/{workflow_id}/<run-id>/<step-id>/sub-agent-prompt.md`. Invoke the sub-agent.
- **State Updating**: Parse the sub-agent's JSON response and its schema. Update `state.md`.

## Sub-Agent Responsibilities
- **Task Execution**: Perform the specific task.
- **Artifact Management**: Save all files to the directory provided by the Main Agent.
- **Evaluation**: Self-evaluate against Success Criteria and return `success`.
- **Routing**: Calculate `nextStep`.

## Route Table
| Current Step | Condition | Next Action |
| --- | --- | --- |
| Any | `success == false` | STOP |
| Any | `success == true` | Read `nextStep` from output |
"""

STEP_TEMPLATE = """# Step: {step_id}

## Step Goal
{purpose}

## Instructions
{instructions_logic}
- **Artifacts**: All generated files must be saved to the **Workspace Directory** provided by the Main Agent.
- **Evaluation**: Evaluate results against Success Criteria to set the `success` field.

## Input
{inputs_list}
- **Workspace Directory**: (Provided by Main Agent) The absolute path for artifact storage.

## Recommend Next Step
{next_step_logic}
- Default: `{recommended_next}`

## Output
- **JSON Schema**: `steps/schemas/{step_id}.schema.json`
- **Fields**:
  - `success`: (Boolean) True if Success Criteria are met.
  - `nextStep`: The ID of the next step.
  - `schema`: Path to the JSON schema.
{outputs_list}

## Success/Failure Criteria
### Success
- Goal achieved and artifacts saved to Workspace Directory.
- Output matches schema.

### Failure
- Artifacts missing or saved to wrong location.
"""

SCHEMA_TEMPLATE = """{{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {{
    "success": {{
      "type": "boolean",
      "description": "True if the step achieved its Success Criteria, false otherwise."
    }},
    "nextStep": {{
      "type": "string",
      "description": "The ID of the next step to execute."
    }},
    "schema": {{
      "type": "string",
      "description": "Path to this schema file."
    }}{additional_properties}
  }},
  "required": ["success", "nextStep", "schema"{required_fields}]
}}
"""

RUN_STATE_TEMPLATE = """---
workflow_id: {workflow_id}
run_id: <run-id>
status: ready
current_step: {entry_step}
progress:
  completed: []
  total_steps: {total_steps}
created_at: <timestamp>
updated_at: <timestamp>
---

# Workflow Run State: {workflow_id}

## Goal
{goal}

## Step Outcomes

"""

FIXTURE_PROMPT_TEMPLATE = """# Test Prompt: {step_id} - {test_case}

## Goal
{purpose}

## Inputs
{inputs_json}

## Instructions
Please execute the step `{step_id}` with the provided inputs. Remember to save artifacts to the workspace directory injected by the Debug Orchestrator.
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
    base_project = Path(project_root).expanduser().resolve()
    
    raw_step_names = [step["name"].strip() for step in steps if step["name"].strip()]
    if not raw_step_names:
        raise ValueError("At least one step is required.")
    step_ids = [build_step_id(index, name) for index, name in enumerate(raw_step_names, start=1)]
    entry_step = step_ids[0]

    write(
        root / "orchestration.md",
        ORCHESTRATION_TEMPLATE.format(
            workflow_id=workflow_id,
            goal=goal,
            entry_step=entry_step,
        ),
    )

    for index, step_id in enumerate(step_ids):
        step_spec = steps[index]
        recommended_next = step_ids[index + 1] if index + 1 < len(step_ids) else "STOP"
        inputs = step_spec.get("inputs_required") or ["context"]
        outputs = step_spec.get("outputs_written") or ["result"]
        
        inputs_list = "\n".join(f"- **{item}**: <Description of {item}>" for item in inputs)
        outputs_list = "\n".join(f"  - `{item}`: <Description of {item}>" for item in outputs)

        write(
            root / "steps" / f"{step_id}.md",
            STEP_TEMPLATE.format(
                step_id=step_id,
                purpose=step_spec.get("purpose", "TODO"),
                instructions_logic=step_spec.get("instructions", "1. Process the inputs.\n2. Generate required artifacts."),
                inputs_list=inputs_list,
                outputs_list=outputs_list,
                recommended_next=recommended_next,
                next_step_logic=step_spec.get("next_step_logic", "- Default to the next sequential step."),
            ),
        )

        additional_props = ""
        required_fields = ""
        for out in outputs:
            additional_props += f',\n    "{out}": {{\n      "type": "string",\n      "description": "Description of {out}"\n    }}'
            required_fields += f', "{out}"'
        
        write(
            root / "steps" / "schemas" / f"{step_id}.schema.json",
            SCHEMA_TEMPLATE.format(
                additional_properties=additional_props,
                required_fields=required_fields
            )
        )
        
        test_case = "happy-path"
        fixture_dir = root / "fixtures" / step_id / test_case
        fixture_input = step_spec.get("fixture_input") or {item: "TODO" for item in inputs}
        
        write(
            fixture_dir / "prompt.md",
            FIXTURE_PROMPT_TEMPLATE.format(
                step_id=step_id,
                test_case=test_case,
                purpose=step_spec.get("purpose", "TODO"),
                inputs_json=json.dumps(fixture_input, indent=2, ensure_ascii=False)
            )
        )

    runs_dir = base_project / "runs" / workflow_id
    write(runs_dir / ".gitkeep", "")
    write(
        runs_dir / "state.example.md",
        RUN_STATE_TEMPLATE.format(
            workflow_id=workflow_id, 
            entry_step=entry_step,
            total_steps=len(step_ids),
            goal=goal
        ),
    )
    
    write(
        root / "workflow.spec.json",
        json.dumps(
            {
                "workflow_id": workflow_id,
                "goal": goal,
                "project_root": str(base_project),
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
    parser = argparse.ArgumentParser(description="Scaffold an AI workflow.")
    parser.add_argument("--workflow-id", required=True, help="Workflow identifier")
    parser.add_argument("--goal", default="TODO", help="Goal")
    parser.add_argument("--project-root", default=".", help="Root")
    parser.add_argument("--target-dir", help="Target")
    parser.add_argument("--steps", default="init,process,complete", help="Steps")
    args = parser.parse_args()

    steps = [{"name": s.strip()} for s in args.steps.split(",") if s.strip()]
    scaffold_workflow(project_root=args.project_root, workflow_id=args.workflow_id, goal=args.goal, steps=steps, target_dir=args.target_dir)

if __name__ == "__main__":
    main()
