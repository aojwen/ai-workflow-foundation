#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(":", "-")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def extract_json_block(markdown: str, marker: str) -> dict[str, Any]:
    pattern = rf"## {re.escape(marker)}\s+```json\s+(.*?)```"
    match = re.search(pattern, markdown, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Missing JSON block under heading: {marker}")
    return json.loads(match.group(1))


def load_orchestration(workflow_dir: Path) -> dict[str, Any]:
    path = workflow_dir / "orchestration.md"
    contract = extract_json_block(read_text(path), "Machine Contract")
    contract["_path"] = str(path)
    return contract


def resolve_workflow_dir(workflow_ref: str, project_root: str | None) -> Path:
    candidate = Path(workflow_ref).expanduser()
    if candidate.exists():
        return candidate.resolve()
    base = Path(project_root or ".").expanduser().resolve()
    resolved = base / ".ai-workflows" / workflow_ref
    if resolved.exists():
        return resolved
    raise FileNotFoundError(
        f"Workflow '{workflow_ref}' not found. Checked '{candidate}' and '{resolved}'."
    )


def step_path(workflow_dir: Path, step_id: str) -> Path:
    candidate = workflow_dir / "steps" / f"{step_id}.md"
    if not candidate.exists():
        raise FileNotFoundError(f"Step file not found: {candidate}")
    return candidate


def load_step(workflow_dir: Path, step_id: str) -> dict[str, Any]:
    path = step_path(workflow_dir, step_id)
    contract = extract_json_block(read_text(path), "Machine Contract")
    contract["_path"] = str(path)
    return contract


def runs_dir(workflow_dir: Path) -> Path:
    return workflow_dir / "runs"


def run_dir(workflow_dir: Path, run_id: str) -> Path:
    return runs_dir(workflow_dir) / run_id


def load_state(workflow_dir: Path, run_id: str) -> dict[str, Any]:
    path = run_dir(workflow_dir, run_id) / "state.json"
    if not path.exists():
        raise FileNotFoundError(f"Run state not found: {path}")
    return json.loads(read_text(path))


def save_state(workflow_dir: Path, run_id: str, state: dict[str, Any]) -> None:
    write_json(run_dir(workflow_dir, run_id) / "state.json", state)


def latest_run_id(workflow_dir: Path) -> str:
    candidates = [p.name for p in runs_dir(workflow_dir).iterdir() if p.is_dir()]
    if not candidates:
        raise FileNotFoundError("No runs found.")
    return sorted(candidates)[-1]


def resolve_value(path: str, output: dict[str, Any]) -> Any:
    current: Any = output
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def choose_next_step(
    orchestration: dict[str, Any],
    current_step: str,
    step_output: dict[str, Any],
) -> tuple[str, str]:
    for route in orchestration.get("routes", []):
        if route.get("from") not in (current_step, "*"):
            continue
        if route.get("when") == "always":
            return route["next_step"], route.get("reason", "route matched")
        if route.get("when") == "output_path_equals":
            value = resolve_value(route["path"], step_output)
            if value == route.get("equals"):
                return route["next_step"], route.get("reason", f"{route['path']} == {route.get('equals')}")
        if route.get("when") == "output_path_truthy":
            value = resolve_value(route["path"], step_output)
            if value:
                return route["next_step"], route.get("reason", f"{route['path']} is truthy")
        if route.get("when") == "output_path_falsey":
            value = resolve_value(route["path"], step_output)
            if not value:
                return route["next_step"], route.get("reason", f"{route['path']} is falsey")
    return step_output.get("recommended_next_step", "STOP"), "step hint fallback"


def command_start(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    orchestration = load_orchestration(workflow_dir)
    run_id = args.run_id or f"run-{utc_stamp()}"
    first_step = orchestration["entry_step"]
    state = {
        "run_id": run_id,
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
    save_state(workflow_dir, run_id, state)
    append_event(
        run_dir(workflow_dir, run_id) / "events.ndjson",
        {"ts": datetime.now(timezone.utc).isoformat(), "type": "run_started", "run_id": run_id, "step": first_step},
    )
    step = load_step(workflow_dir, first_step)
    print(json.dumps({
        "run_id": run_id,
        "status": state["status"],
        "current_step": first_step,
        "step_file": step["_path"],
        "expected_inputs": step.get("inputs_required", []),
        "fixture_hint": str(workflow_dir / "fixtures" / first_step / "input.json"),
    }, indent=2, ensure_ascii=False))
    return 0


def command_status(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    run_id = args.run_id or latest_run_id(workflow_dir)
    state = load_state(workflow_dir, run_id)
    current_step = state.get("current_step")
    payload = {
        "run_id": run_id,
        "workflow_id": state["workflow_id"],
        "status": state["status"],
        "current_step": current_step,
        "completed_steps": state["completed_steps"],
        "route_decision": state["route_decision"],
    }
    if current_step and current_step != "STOP":
        payload["step_file"] = str(step_path(workflow_dir, current_step))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_advance(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    run_id = args.run_id or latest_run_id(workflow_dir)
    state = load_state(workflow_dir, run_id)
    orchestration = load_orchestration(workflow_dir)
    current_step = state.get("current_step")
    if not current_step or current_step == "STOP":
        raise ValueError("Run is already complete.")

    step_output = json.loads(Path(args.step_output_file).read_text(encoding="utf-8"))
    artifacts_dir = run_dir(workflow_dir, run_id) / "artifacts"
    write_json(artifacts_dir / f"{current_step}.output.json", step_output)

    state["step_outputs"][current_step] = step_output
    if current_step not in state["completed_steps"]:
        state["completed_steps"].append(current_step)

    next_step, reason = choose_next_step(orchestration, current_step, step_output)
    state["route_decision"] = {"chosen_next_step": next_step, "reason": reason}
    state["current_step"] = None if next_step == "STOP" else next_step
    state["status"] = "completed" if next_step == "STOP" else "ready"
    state["route_decision"]["decided_by"] = "main-agent"
    state["route_decision"]["timestamp"] = datetime.now(timezone.utc).isoformat()
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

    result = {
        "run_id": run_id,
        "completed_step": current_step,
        "next_step": next_step,
        "status": state["status"],
        "reason": reason,
    }
    if next_step != "STOP":
        result["next_step_file"] = str(step_path(workflow_dir, next_step))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def command_debug_step(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    step = load_step(workflow_dir, args.step_id)
    debug_run_id = args.run_id or f"debug-{utc_stamp()}"
    target_dir = run_dir(workflow_dir, debug_run_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    fixture = Path(args.fixture).resolve() if args.fixture else workflow_dir / "fixtures" / args.step_id / "input.json"
    snapshot = Path(args.snapshot).resolve() if args.snapshot else None

    debug_payload = {
        "run_id": debug_run_id,
        "mode": "debug-step",
        "step_id": args.step_id,
        "step_file": step["_path"],
        "fixture": str(fixture),
        "snapshot": str(snapshot) if snapshot else None,
        "observed_output_file": str(target_dir / "artifacts" / f"{args.step_id}.observed.json"),
        "report_file": str(target_dir / "debug-report.json"),
    }
    write_json(target_dir / "debug-session.json", debug_payload)
    print(json.dumps(debug_payload, indent=2, ensure_ascii=False))
    return 0


def command_snapshot_step(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    run_id = args.run_id or latest_run_id(workflow_dir)
    state = load_state(workflow_dir, run_id)
    step_id = args.step_id or state.get("current_step")
    if not step_id:
        raise ValueError("No step available to snapshot.")

    snapshot_name = args.name or utc_stamp()
    snapshot_dir = workflow_dir / "snapshots" / step_id / snapshot_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    write_json(snapshot_dir / "state-before.json", state)
    fixture_path = workflow_dir / "fixtures" / step_id / "input.json"
    if fixture_path.exists():
        shutil.copy2(fixture_path, snapshot_dir / "input.json")
    last_output = run_dir(workflow_dir, run_id) / "artifacts" / f"{step_id}.output.json"
    if last_output.exists():
        shutil.copy2(last_output, snapshot_dir / "last-output.json")

    print(json.dumps({
        "run_id": run_id,
        "step_id": step_id,
        "snapshot_dir": str(snapshot_dir),
    }, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run and debug step-based AI workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("workflow_ref")
    start.add_argument("--project-root", default=".")
    start.add_argument("--run-id")
    start.set_defaults(func=command_start)

    status = subparsers.add_parser("status")
    status.add_argument("workflow_ref")
    status.add_argument("--project-root", default=".")
    status.add_argument("--run-id")
    status.set_defaults(func=command_status)

    advance = subparsers.add_parser("advance")
    advance.add_argument("workflow_ref")
    advance.add_argument("--project-root", default=".")
    advance.add_argument("--run-id")
    advance.add_argument("--step-output-file", required=True)
    advance.set_defaults(func=command_advance)

    debug_step = subparsers.add_parser("debug-step")
    debug_step.add_argument("workflow_ref")
    debug_step.add_argument("--project-root", default=".")
    debug_step.add_argument("--step-id", required=True)
    debug_step.add_argument("--fixture")
    debug_step.add_argument("--snapshot")
    debug_step.add_argument("--run-id")
    debug_step.set_defaults(func=command_debug_step)

    snapshot = subparsers.add_parser("snapshot-step")
    snapshot.add_argument("workflow_ref")
    snapshot.add_argument("--project-root", default=".")
    snapshot.add_argument("--run-id")
    snapshot.add_argument("--step-id")
    snapshot.add_argument("--name")
    snapshot.set_defaults(func=command_snapshot_step)

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
