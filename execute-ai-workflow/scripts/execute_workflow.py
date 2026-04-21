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
)


def default_submission_path(workflow_dir: Path, run_id: str, step_id: str) -> Path:
    return run_dir(workflow_dir, run_id) / "submissions" / f"{step_id}.json"


def starter_output_template(step_contract: dict[str, Any]) -> dict[str, Any]:
    outputs = step_contract.get("outputs_written", [])
    template: dict[str, Any] = {
        "step_id": step_contract["step_id"],
        "recommended_next_step": step_contract.get("recommended_next_step", "STOP"),
    }
    for name in outputs:
        template[name] = ""
    return template


def build_step_packet(workflow_dir: Path, run_id: str, state: dict[str, Any]) -> dict[str, Any]:
    workflow_dir = workflow_dir.resolve()
    current_step = state.get("current_step")
    if not current_step:
        return {
            "mode": "execute",
            "run_id": run_id,
            "workflow_id": state["workflow_id"],
            "status": state["status"],
            "completed_steps": state.get("completed_steps", []),
            "message": "Workflow is complete.",
        }

    orchestration = load_orchestration(workflow_dir)
    step_contract = load_step(workflow_dir, current_step)
    step_file = Path(step_contract["_path"])
    step_markdown = read_text(step_file)
    fixture_path = workflow_dir / "fixtures" / current_step / "input.json"
    submission_path = default_submission_path(workflow_dir, run_id, current_step)
    output_template = starter_output_template(step_contract)
    if not submission_path.exists():
        write_json(submission_path, output_template)

    return {
        "mode": "execute",
        "workflow_id": state["workflow_id"],
        "workflow_dir": str(workflow_dir),
        "orchestration_file": orchestration["_path"],
        "run_id": run_id,
        "status": state["status"],
        "current_step": current_step,
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
        },
        "route_context": state.get("route_decision", {}),
    }


def advance_once(workflow_dir: Path, run_id: str, step_output_file: Path) -> dict[str, Any]:
    from run_workflow import choose_next_step, append_event, save_state, load_orchestration
    from datetime import datetime, timezone

    state = load_state(workflow_dir, run_id)
    orchestration = load_orchestration(workflow_dir)
    current_step = state.get("current_step")
    if not current_step or current_step == "STOP":
        raise ValueError("Run is already complete.")

    step_output = json.loads(step_output_file.read_text(encoding="utf-8"))
    artifacts_dir = run_dir(workflow_dir, run_id) / "artifacts"
    write_json(artifacts_dir / f"{current_step}.output.json", step_output)

    state["step_outputs"][current_step] = step_output
    if current_step not in state["completed_steps"]:
        state["completed_steps"].append(current_step)

    next_step, reason = choose_next_step(orchestration, current_step, step_output)
    state["route_decision"] = {
        "chosen_next_step": next_step,
        "reason": reason,
        "decided_by": "main-agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state["current_step"] = None if next_step == "STOP" else next_step
    state["status"] = "completed" if next_step == "STOP" else "ready"
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_state(workflow_dir, run_id, state)
    append_event(
        run_dir(workflow_dir, run_id) / "events.ndjson",
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "step_completed",
            "run_id": run_id,
            "step": current_step,
            "next_step": next_step,
            "reason": reason,
        },
    )
    return state


def ensure_run(workflow_dir: Path, run_id: str | None = None) -> str:
    from run_workflow import load_orchestration, save_state, append_event
    from datetime import datetime, timezone

    if run_id:
        state_path = run_dir(workflow_dir, run_id) / "state.json"
        if state_path.exists():
            return run_id

    orchestration = load_orchestration(workflow_dir)
    chosen_run_id = run_id or f"run-{utc_stamp()}"
    first_step = orchestration["entry_step"]
    state = {
        "run_id": chosen_run_id,
        "workflow_id": orchestration["workflow_id"],
        "status": "ready",
        "current_step": first_step,
        "completed_steps": [],
        "step_outputs": {},
        "artifacts": [],
        "route_decision": {
            "chosen_next_step": first_step,
            "reason": "entry step",
            "decided_by": "main-agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "blockers": [],
        "retry_state": {
            "step_id": None,
            "attempt_count": 0,
            "last_failure_reason": None,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(workflow_dir, chosen_run_id, state)
    append_event(
        run_dir(workflow_dir, chosen_run_id) / "events.ndjson",
        {"ts": datetime.now(timezone.utc).isoformat(), "type": "run_started", "run_id": chosen_run_id, "step": first_step},
    )
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
    current_step = state.get("current_step")
    if not current_step:
        print(json.dumps(build_step_packet(workflow_dir, run_id, state), indent=2, ensure_ascii=False))
        return 0

    step_output_file = Path(args.step_output_file).resolve() if args.step_output_file else default_submission_path(workflow_dir, run_id, current_step)
    if not step_output_file.exists():
        raise FileNotFoundError(f"Step output file not found: {step_output_file}")

    updated_state = advance_once(workflow_dir, run_id, step_output_file)
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
