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
    raise FileNotFoundError(f"Workflow '{workflow_ref}' not found.")


def step_path(workflow_dir: Path, step_id: str) -> Path:
    return workflow_dir / "steps" / f"{step_id}.md"


def load_step(workflow_dir: Path, step_id: str) -> dict[str, Any]:
    path = step_path(workflow_dir, step_id)
    contract = extract_json_block(read_text(path), "Machine Contract")
    contract["_path"] = str(path)
    return contract


def run_dir(workflow_dir: Path, run_id: str) -> Path:
    return workflow_dir / "runs" / run_id


def load_state_full(workflow_dir: Path, run_id: str) -> tuple[dict[str, Any], str]:
    path = run_dir(workflow_dir, run_id) / "state.md"
    if not path.exists():
        raise FileNotFoundError(f"Run state not found: {path}")
    content = read_text(path)
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if match:
        return json.loads(match.group(1)), match.group(2)
    raise ValueError("Invalid state.md format")


def load_state(workflow_dir: Path, run_id: str) -> dict[str, Any]:
    state, _ = load_state_full(workflow_dir, run_id)
    return state


def save_state_full(workflow_dir: Path, run_id: str, state: dict[str, Any], body: str) -> None:
    path = run_dir(workflow_dir, run_id) / "state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{json.dumps(state, indent=2, ensure_ascii=False)}\n---\n{body}", encoding="utf-8")


def latest_run_id(workflow_dir: Path) -> str:
    candidates = [p.name for p in (workflow_dir / "runs").iterdir() if p.is_dir()]
    if not candidates:
        raise FileNotFoundError("No runs found.")
    return sorted(candidates)[-1]


def resolve_value(path: str, context: dict[str, Any]) -> Any:
    # Supports "step-id.field" dot-notation
    parts = path.split(".")
    current = context
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def process_step_submission(workflow_dir: Path, run_id: str, step_id: str, step_output: dict[str, Any]) -> dict[str, Any]:
    state, body = load_state_full(workflow_dir, run_id)
    
    # 1. Update Completion
    if step_id in state.get("active_steps", []):
        state["active_steps"].remove(step_id)
    if step_id not in state.get("completed_steps", []):
        state.setdefault("completed_steps", []).append(step_id)
    state.setdefault("step_outputs", {})[step_id] = step_output
    
    body += f"\n### Step {step_id} Output\n```json\n{json.dumps(step_output, indent=2)}\n```\n"

    # 2. Collect Next Step Signals
    emitted = step_output.get("nextSteps", [])
    if isinstance(emitted, str): emitted = [emitted]
    for ns in emitted:
        if ns and ns != "STOP" and ns not in state.get("pending_signals", []):
            if ns not in state.get("completed_steps", []) and ns not in state.get("active_steps", []):
                state.setdefault("pending_signals", []).append(ns)

    # 3. Reactive Routing & Validation
    orchestration = load_orchestration(workflow_dir)
    routing_table = orchestration.get("routing_table", {})
    newly_activated = []
    
    for pending in list(state.get("pending_signals", [])):
        config = routing_table.get(pending, {})
        depends_on = config.get("depends_on", [])
        required_inputs = config.get("required_inputs", {})
        
        # Condition A: Are all dependencies done? (Hard Gate)
        deps_met = all(d in state["completed_steps"] for d in depends_on)
        if not deps_met:
            continue # Still waiting for other steps
            
        # Condition B: Are all inputs matching expected values?
        missing_or_invalid_inputs = {}
        
        if isinstance(required_inputs, dict):
            for inp_path, expected_value in required_inputs.items():
                actual_value = resolve_value(inp_path, state.get("step_outputs", {}))
                if actual_value != expected_value:
                    missing_or_invalid_inputs[inp_path] = {"expected": expected_value, "actual": actual_value}
        elif isinstance(required_inputs, list):
            # Fallback for older schemas without expected values
            for inp_path in required_inputs:
                if resolve_value(inp_path, state.get("step_outputs", {})) is None:
                    missing_or_invalid_inputs[inp_path] = {"expected": "ANY_NON_NULL", "actual": None}

        if not missing_or_invalid_inputs:
            # Trigger!
            state["pending_signals"].remove(pending)
            newly_activated.append(pending)
        else:
            # Fail-Fast! Depends_on is met but inputs are missing or invalid.
            state["status"] = "failed"
            state["error"] = f"Step {pending} failed input contract validation: {missing_or_invalid_inputs}"
            body += f"\n### ERROR: Step {pending} blocked.\nFailed input contract validation:\n```json\n{json.dumps(missing_or_invalid_inputs, indent=2)}\n```\n"
            save_state_full(workflow_dir, run_id, state, body)
            return state

    state.setdefault("active_steps", []).extend(newly_activated)
    
    # 4. Check Finality
    if not state["active_steps"]:
        if state.get("pending_signals"):
            state["status"] = "failed"
            state["error"] = "Deadlock: Pending steps cannot satisfy dependencies."
        else:
            state["status"] = "completed"
            
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_state_full(workflow_dir, run_id, state, body)
    return state


def command_start(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    orchestration = load_orchestration(workflow_dir)
    run_id = args.run_id or f"run-{utc_stamp()}"
    first_step = orchestration["entry_step"]
    state = {
        "run_id": run_id, "workflow_id": orchestration["workflow_id"],
        "status": "ready", "active_steps": [first_step],
        "completed_steps": [], "pending_signals": [], "step_outputs": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    body = f"# Workflow Run State: {orchestration['workflow_id']}\n"
    save_state_full(workflow_dir, run_id, state, body)
    print(json.dumps({"run_id": run_id, "active_steps": [first_step]}, indent=2))
    return 0


def command_status(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    run_id = args.run_id or latest_run_id(workflow_dir)
    state = load_state(workflow_dir, run_id)
    payload = {
        "run_id": run_id,
        "workflow_id": state["workflow_id"],
        "status": state["status"],
        "active_steps": state.get("active_steps", []),
        "completed_steps": state.get("completed_steps", []),
        "pending_signals": state.get("pending_signals", []),
        "error": state.get("error"),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_advance(args: argparse.Namespace) -> int:
    workflow_dir = resolve_workflow_dir(args.workflow_ref, args.project_root)
    run_id = args.run_id or latest_run_id(workflow_dir)
    state = load_state(workflow_dir, run_id)
    step_id = args.step_id
    if not step_id:
        active = state.get("active_steps", [])
        if len(active) == 1: step_id = active[0]
        else: raise ValueError("--step-id is required.")
    
    output = json.loads(Path(args.step_output_file).read_text(encoding="utf-8"))
    st = process_step_submission(workflow_dir, run_id, step_id, output)
    print(json.dumps({"run_id": run_id, "completed_step": step_id, "status": st["status"], "active_steps": st.get("active_steps", [])}, indent=2))
    return 0


def command_debug_step(args: argparse.Namespace) -> int:
    # Debug implementation elided for brevity, using standard signature
    print(json.dumps({"mode": "debug-step", "step_id": args.step_id}))
    return 0


def command_snapshot_step(args: argparse.Namespace) -> int:
    # Snapshot implementation elided for brevity
    print(json.dumps({"mode": "snapshot", "step_id": args.step_id}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    
    start = sub.add_parser("start")
    start.add_argument("workflow_ref")
    start.add_argument("--project-root", default=".")
    start.add_argument("--run-id")
    start.set_defaults(func=command_start)
    
    status = sub.add_parser("status")
    status.add_argument("workflow_ref")
    status.add_argument("--project-root", default=".")
    status.add_argument("--run-id")
    status.set_defaults(func=command_status)
    
    advance = sub.add_parser("advance")
    advance.add_argument("workflow_ref")
    advance.add_argument("--project-root", default=".")
    advance.add_argument("--run-id")
    advance.add_argument("--step-id")
    advance.add_argument("--step-output-file", required=True)
    advance.set_defaults(func=command_advance)

    debug = sub.add_parser("debug-step")
    debug.add_argument("workflow_ref")
    debug.add_argument("--step-id", required=True)
    debug.set_defaults(func=command_debug_step)

    snapshot = sub.add_parser("snapshot-step")
    snapshot.add_argument("workflow_ref")
    snapshot.add_argument("--step-id", required=True)
    snapshot.set_defaults(func=command_snapshot_step)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
