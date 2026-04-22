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

def load_routing_table(workflow_dir: Path) -> dict[str, Any]:
    path = workflow_dir / "routing.json"
    if not path.exists():
        # Fallback to orchestration.md for backwards compatibility with older workflows
        return load_orchestration(workflow_dir).get("routing_table", {})
    return json.loads(read_text(path))

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
    # In the future, step contracts could also be stripped from LLM view, 
    # but for now they stay in steps/*.md. Let's extract safely.
    path = step_path(workflow_dir, step_id)
    try:
        contract = extract_json_block(read_text(path), "Machine Contract")
    except ValueError:
        # Fallback if the step file format was updated to hide contract
        schema_path = workflow_dir / "steps" / "schemas" / f"{step_id}.schema.json"
        contract = {
            "step_id": step_id,
            "outputs_written": []
        }
        if schema_path.exists():
            schema = json.loads(read_text(schema_path))
            props = schema.get("properties", {})
            contract["outputs_written"] = [k for k in props.keys() if k not in ["success", "nextSteps", "schema"]]
            
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
    runs_path = workflow_dir / "runs"
    if not runs_path.exists():
        raise FileNotFoundError(f"Runs directory not found: {runs_path}")
    candidates = [p.name for p in runs_path.iterdir() if p.is_dir()]
    if not candidates:
        raise FileNotFoundError("No runs found.")
    return sorted(candidates)[-1]

def resolve_value(path: str, context: dict[str, Any]) -> Any:
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
    
    if "completed_steps" not in state: state["completed_steps"] = []
    if step_id not in state["completed_steps"]:
        state["completed_steps"].append(step_id)
        
    if step_id in state.get("active_steps", []):
        state["active_steps"].remove(step_id)
        
    state.setdefault("step_outputs", {})[step_id] = step_output
    
    body += f"\n### Step {step_id} Output\n```json\n{json.dumps(step_output, indent=2)}\n```\n"

    emitted = step_output.get("nextSteps", [])
    if isinstance(emitted, str): emitted = [emitted]
    for ns in emitted:
        if ns and ns != "STOP" and ns not in state.get("pending_signals", []) and ns not in state.get("completed_steps", []):
            state.setdefault("pending_signals", []).append(ns)

    # -------------------------------------------------------------
    # ADMISSION CONTROL (Using dedicated routing.json)
    # -------------------------------------------------------------
    routing_table = load_routing_table(workflow_dir)
    newly_activated = []
    
    for pending in list(state.get("pending_signals", [])):
        condition_sets = routing_table.get(pending, [])
        if not isinstance(condition_sets, list): condition_sets = [condition_sets]
        
        step_is_blocked_by_deps = False
        any_condition_set_satisfied = False
        validation_errors = []

        for cs in condition_sets:
            deps = cs.get("depends_on", [])
            inputs = cs.get("required_inputs", {})
            
            if not all(d in state["completed_steps"] for d in deps):
                step_is_blocked_by_deps = True
                continue
            
            mismatch = {k: {"exp": v, "act": resolve_value(k, state["step_outputs"])} 
                       for k, v in inputs.items() if resolve_value(k, state["step_outputs"]) != v}
            
            if not mismatch:
                any_condition_set_satisfied = True
                break
            else:
                validation_errors.append(mismatch)

        if any_condition_set_satisfied:
            state["pending_signals"].remove(pending)
            newly_activated.append(pending)
        elif not step_is_blocked_by_deps and validation_errors:
            state["status"] = "failed"
            state["error"] = f"Admission denied for {pending}. No condition sets satisfied: {validation_errors}"
            body += f"\n### ERROR: Admission Denied for {pending}\nFailed all {len(validation_errors)} condition sets.\n"
            save_state_full(workflow_dir, run_id, state, body)
            return state

    state.setdefault("active_steps", []).extend(newly_activated)
    if not state["active_steps"]:
        state["status"] = "failed" if state.get("pending_signals") else "completed"
    
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_state_full(workflow_dir, run_id, state, body)
    return state
