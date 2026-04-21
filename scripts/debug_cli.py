#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

# The standardized "Main Agent Prompt" for Debug Mode
DEBUG_EXECUTION_WRAPPER = """You are a sub-agent executing a workflow step in DEBUG MODE.

CRITICAL WORKSPACE INSTRUCTION:
You MUST save all generated files, artifacts, and complex data structures to the following isolated directory:
{workspace_dir}
Do NOT save files to any other location. Return the absolute file paths in your final flat JSON response.

--- ORIGINAL STEP PROMPT BELOW ---

{step_prompt}
"""

DEBUG_VALIDATION_PROMPT = """You are the Main Orchestrator Agent evaluating a sub-agent's debug output.

# Validation Task
Analyze the sub-agent's response against the expected outcome and specific assertions.
Ensure the sub-agent correctly followed the Workspace Instructions and provided a valid 'success' boolean.

# Expected Outcome
{expected_content}

# Assertions
{assertions_content}

# Sub-Agent Response
{response}

Evaluate strictly. Provide reasoning and end with:
RESULT_PASS or RESULT_FAIL
"""

def run_claude(prompt: str, project_root: str = ".") -> str:
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--dangerously-skip-permissions"],
            capture_output=True,
            text=True,
            check=True,
            cwd=project_root
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error executing claude: {e.stderr}"
    except FileNotFoundError:
        return "Error: 'claude' CLI not found in PATH."

def execute_test_case(workflow_id: str, step_id: str, test_case: str, project_root: str) -> dict:
    base_project = Path(project_root).expanduser().resolve()
    fixture_dir = base_project / ".ai-workflows" / workflow_id / "fixtures" / step_id / test_case
    
    # 1. Read static definition
    prompt_content = (fixture_dir / "prompt.md").read_text(encoding="utf-8")
    expected_content = (fixture_dir / "expected.md").read_text(encoding="utf-8") if (fixture_dir / "expected.md").exists() else ""
    assertions_content = (fixture_dir / "assertions.md").read_text(encoding="utf-8") if (fixture_dir / "assertions.md").exists() else ""

    # 2. Setup isolated run directory: debugs/<workflow-id>/<step-id>/<test-case>/<run-id>/
    import datetime
    run_id = datetime.datetime.now().strftime("run-%Y%m%d-%H%M%S")
    debug_run_dir = base_project / "debugs" / workflow_id / step_id / test_case / run_id
    debug_run_dir.mkdir(parents=True, exist_ok=True)

    # 3. Spawn Sub-Agent with Wrapper
    print(f"[{test_case}] Run ID: {run_id}")
    print(f"[{test_case}] Spawning Sub-Agent...")
    final_prompt = DEBUG_EXECUTION_WRAPPER.format(workspace_dir=debug_run_dir.absolute(), step_prompt=prompt_content)
    
    start_time = time.time()
    response = run_claude(final_prompt, project_root)
    exec_time = time.time() - start_time

    # 4. Validate Output
    print(f"[{test_case}] Validating Results...")
    val_prompt = DEBUG_VALIDATION_PROMPT.format(expected_content=expected_content, assertions_content=assertions_content, response=response)
    
    val_start = time.time()
    val_response = run_claude(val_prompt, project_root)
    val_time = time.time() - val_start

    passed = "RESULT_PASS" in val_response
    
    # 5. Record Logs
    (debug_run_dir / "sub-agent-prompt.md").write_text(final_prompt, encoding="utf-8")
    (debug_run_dir / "response.json").write_text(response, encoding="utf-8")
    (debug_run_dir / "validation.md").write_text(val_response, encoding="utf-8")
    
    result = {
        "passed": passed,
        "execution_time": exec_time,
        "validation_time": val_time,
        "workspace": str(debug_run_dir)
    }
    (debug_run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--test-case", default="happy-path")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    res = execute_test_case(args.workflow, args.step, args.test_case, args.project_root)
    print(f"Result: {'PASS' if res['passed'] else 'FAIL'}")

if __name__ == "__main__":
    main()
