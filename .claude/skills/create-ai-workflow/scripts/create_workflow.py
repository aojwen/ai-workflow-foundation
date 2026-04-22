#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from init_workflow import scaffold_workflow, slugify


def read_spec(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize(spec: dict, target_dir: str) -> str:
    lines = [
        f"workflow_id: {spec['workflow_id']}",
        f"goal: {spec['goal']}",
        f"target_dir: {target_dir}",
        f"orchestration_model: {spec.get('orchestration_model', 'main-agent-routes-sub-agents-execute')}",
        "steps:",
    ]
    for index, step in enumerate(spec["steps"], start=1):
        lines.append(f"  {index}. {step['name']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create an AI workflow from a confirmed structured spec.")
    parser.add_argument("--spec-file", required=True, help="JSON spec file collected from guided questioning")
    parser.add_argument("--confirm", action="store_true", help="Required flag to actually create the workflow")
    parser.add_argument("--print-summary", action="store_true", help="Print the resolved creation summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    spec_path = Path(args.spec_file).expanduser().resolve()
    spec = read_spec(spec_path)

    workflow_id = slugify(spec["workflow_id"])
    project_root = str(Path(spec.get("project_root", ".")).expanduser().resolve())
    target_dir = spec.get("target_dir") or str(Path(project_root) / ".ai-workflows" / workflow_id)

    if args.print_summary:
        print(summarize(spec, target_dir))

    if not args.confirm:
        print(
            json.dumps(
                {
                    "status": "awaiting_confirmation",
                    "summary": summarize(spec, target_dir),
                    "message": "Re-run with --confirm after the user explicitly approves this workflow plan.",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    root = scaffold_workflow(
        project_root=project_root,
        workflow_id=workflow_id,
        goal=spec["goal"],
        steps=spec["steps"],
        target_dir=target_dir,
        metadata={
            "source_spec_file": str(spec_path),
            "creator": "create_workflow.py",
        },
    )
    print(
        json.dumps(
            {
                "status": "created",
                "workflow_id": workflow_id,
                "workflow_dir": str(root),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
