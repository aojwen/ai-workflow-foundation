#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from run_workflow import (
    load_orchestration,
    load_state,
    load_step,
    latest_run_id,
    read_text,
    resolve_workflow_dir,
    run_dir,
    utc_stamp,
    write_json,
    process_step_submission,
)


def default_submission_path(workflow_dir: Path, run_id: str, step_id: str) -> Path:
    return run_dir(workflow_dir, run_id) / "submissions" / f"{step_id}.json"


def starter_output_template(step_contract: dict[str, Any]) -> dict[str, Any]:
    outputs = step_contract.get("outputs_written", [])
    template: dict[str, Any] = {
        "step_id": step_contract.get("step_id", "unknown"),
        "nextSteps": step_contract.get("recommended_next_steps", []),
    }
    for name in outputs:
        template[name] = ""
    return template


def build_step_packet(workflow_dir: Path, run_id: str, state: dict[str, Any]) -> dict[str, Any]:
    workflow_dir = workflow_dir.resolve()
    
    active_steps = state.get("active_steps", [])
    if "current_step" in state and state["current_step"]:
         active_steps = [state["current_step"]]
         
    if not active_steps:
        return {
            "mode": "execute",
            "run_id": run_id,
            "workflow_id": state.get("workflow_id", "unknown"),
            "status": state.get("status", "completed"),
            "completed_steps": state.get("completed_steps", []),
            "message": "Workflow is complete or deadlocked.",
            "error": state.get("error")
        }

    orchestration = load_orchestration(workflow_dir)
    
    steps_data = []
    for step_id in active_steps:
        step_contract = load_step(workflow_dir, step_id)
        step_contract["step_id"] = step_id
        step_file = Path(step_contract["_path"])
        step_markdown = read_text(step_file)
        fixture_path = workflow_dir / "fixtures" / step_id / "input.json"
        submission_path = default_submission_path(workflow_dir, run_id, step_id)
        output_template = starter_output_template(step_contract)
        if not submission_path.exists():
            write_json(submission_path, output_template)

        steps_data.append({
            "step_id": step_id,
            "step_file": str(step_file),
            "step_contract": {
                key: value
                for key, value in step_contract.items()
                if key != "_path"
            },
            "step_markdown": step_markdown,
            "available_inputs": {
                "fixture_file": str(fixture_path) if fixture_path.exists() else None,
                "step_outputs_from_previous_steps": state.get("step_outputs", {}),
                "completed_steps": state.get("completed_steps", []),
            },
            "submission": {
                "step_output_file": str(submission_path),
                "starter_template": output_template,
            }
        })

    return {
        "mode": "execute",
        "workflow_id": state.get("workflow_id", "unknown"),
        "workflow_dir": str(workflow_dir),
        "orchestration_file": orchestration.get("_path", ""),
        "run_id": run_id,
        "status": state.get("status", "ready"),
        "active_steps": steps_data
    }


def advance_once(workflow_dir: Path, run_id: str, step_id: str, step_output_file: Path) -> dict[str, Any]:
    step_output = json.loads(step_output_file.read_text(encoding="utf-8"))
    return process_step_submission(workflow_dir, run_id, step_id, step_output)


def ensure_run(workflow_dir: Path, run_id: str | None = None) -> str:
    import argparse
    if run_id:
        state_path = run_dir(workflow_dir, run_id) / "state.md"
        if state_path.exists():
            return run_id
            
    from run_workflow import load_orchestration, save_state_full, append_event, utc_stamp
    from datetime import datetime, timezone
    
    orchestration = load_orchestration(workflow_dir)
    chosen_run_id = run_id or f"run-{utc_stamp()}"
    first_step = orchestration["entry_step"]
    
    state = {
        "run_id": chosen_run_id,
        "workflow_id": orchestration["workflow_id"],
        "status": "ready",
        "active_steps": [first_step],
        "completed_steps": [],
        "pending_signals": [],
        "step_outputs": {},
        "artifacts": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    body = f"# Workflow Run State: {orchestration['workflow_id']}\n\n## Step Outcomes\n"
    save_state_full(workflow_dir, chosen_run_id, state, body)
    return chosen_run_id


def command_begin(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    if args.resume:
        run_id = args.run_id or latest_run_id(workflow_dir)
    else:
        run_id = ensure_run(workflow_dir, args.run_id)
    state = load_state(workflow_dir, run_id)
    print(json.dumps(build_step_packet(workflow_dir, run_id, state), indent=2, ensure_ascii=False))
    return 0


def command_submit(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    run_id = args.run_id or latest_run_id(workflow_dir)
    state = load_state(workflow_dir, run_id)
    
    active_steps = state.get("active_steps", [])
    if "current_step" in state and state["current_step"]:
        active_steps = [state["current_step"]]

    if not active_steps:
        print(json.dumps(build_step_packet(workflow_dir, run_id, state), indent=2, ensure_ascii=False))
        return 0
        
    step_id = args.step_id
    if not step_id:
        if len(active_steps) == 1:
            step_id = active_steps[0]
        else:
            raise ValueError("--step-id is required when multiple steps are active.")

    step_output_file = Path(args.step_output_file).resolve() if args.step_output_file else default_submission_path(workflow_dir, run_id, step_id)
    if not step_output_file.exists():
        raise FileNotFoundError(f"Step output file not found: {step_output_file}")

    updated_state = advance_once(workflow_dir, run_id, step_id, step_output_file)
    print(json.dumps(build_step_packet(workflow_dir, run_id, updated_state), indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="High-level execution helper for AI workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    begin = subparsers.add_parser("begin")
    begin.add_argument("workflow_ref")
    begin.add_argument("--project-root", default=".")
    begin.add_argument("--run-id")
    begin.add_argument("--resume", action="store_true")
    begin.set_defaults(func=command_begin)

    submit = subparsers.add_parser("submit")
    submit.add_argument("workflow_ref")
    submit.add_argument("--project-root", default=".")
    submit.add_argument("--run-id")
    submit.add_argument("--step-id")
    submit.add_argument("--step-output-file")
    submit.set_defaults(func=command_submit)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
