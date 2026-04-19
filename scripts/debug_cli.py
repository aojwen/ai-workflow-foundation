#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

def run_claude(prompt: str) -> str:
    """Execute a prompt using the claude CLI."""
    try:
        # Using -p for prompt input. We write prompt to a temp file to avoid shell escaping issues.
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write(prompt)
            temp_path = f.name
            
        result = subprocess.run(
            ["claude", "-p", f"$(cat {temp_path})"], # Assuming claude CLI can take piped or substituted input, but direct file passing might be better.
            # Actually, standard way if it takes -p "string":
            # subprocess.run(["claude", "-p", prompt])
            # But prompt might be very long. Let's try direct text.
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            check=True
        )
        os.remove(temp_path)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error executing claude: {e.stderr}"
    except FileNotFoundError:
        return "Error: 'claude' CLI not found. Please ensure it is installed and in your PATH."

def execute_test_case(workflow_id: str, step_id: str, test_case: str, project_root: str) -> dict:
    base_dir = Path(project_root) / ".ai-workflows" / workflow_id / "fixtures" / step_id / test_case
    
    prompt_file = base_dir / "prompt.md"
    expected_file = base_dir / "expected.md"
    assertions_file = base_dir / "assertions.md"
    
    if not prompt_file.exists():
        return {"status": "error", "message": f"Prompt file not found: {prompt_file}"}

    prompt_content = prompt_file.read_text(encoding="utf-8")
    expected_content = expected_file.read_text(encoding="utf-8") if expected_file.exists() else ""
    assertions_content = assertions_file.read_text(encoding="utf-8") if assertions_file.exists() else ""

    print(f"[{test_case}] Executing sub-agent task...")
    start_time = time.time()
    response = run_claude(prompt_content)
    exec_time = time.time() - start_time

    print(f"[{test_case}] Validating response...")
    validation_prompt = f"""
You are the Main Orchestrator Agent evaluating a sub-agent's output.

# Step Expected Output
{expected_content}

# Assertions to Check
{assertions_content}

# Sub-Agent Response
{response}

Evaluate the response against the assertions.
Provide your reasoning, and end your response with exactly one of these words on a new line:
RESULT_PASS
RESULT_FAIL
"""
    val_start = time.time()
    validation_response = run_claude(validation_prompt)
    val_time = time.time() - val_start

    passed = "RESULT_PASS" in validation_response

    import datetime
    timestamp = datetime.datetime.now().isoformat()
    debug_out_dir = Path(project_root) / "debugs" / workflow_id / step_id / test_case
    debug_out_dir.mkdir(parents=True, exist_ok=True)
    
    (debug_out_dir / "response.md").write_text(response, encoding="utf-8")
    (debug_out_dir / "validation.md").write_text(validation_response, encoding="utf-8")
    
    result_dict = {
        "status": "success",
        "test_case": test_case,
        "prompt": prompt_content,
        "response": response,
        "validation_reasoning": validation_response,
        "passed": passed,
        "execution_time": exec_time,
        "validation_time": val_time,
        "timestamp": timestamp
    }
    
    (debug_out_dir / "result.json").write_text(json.dumps(result_dict, indent=2, ensure_ascii=False), encoding="utf-8")

    return result_dict

def generate_html_report(workflow: str, step: str, results: list, out_path: Path):
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Debug Report: {workflow} / {step}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 20px; color: #333; background: #f5f5f7; }}
        h1 {{ font-weight: 600; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .pass {{ color: #34c759; font-weight: bold; }}
        .fail {{ color: #ff3b30; font-weight: bold; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 8px; white-space: pre-wrap; font-size: 13px; }}
        .times {{ color: #8e8e93; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>Debug Report: {workflow} > {step}</h1>
"""
    for res in results:
        status_class = "pass" if res.get("passed") else "fail"
        status_text = "PASS" if res.get("passed") else "FAIL"
        
        if res.get("status") == "error":
             html += f"""
             <div class="card">
                 <h2>{res['test_case']} - <span class="fail">ERROR</span></h2>
                 <p>{res.get('message')}</p>
             </div>
             """
             continue

        html += f"""
    <div class="card">
        <h2>{res['test_case']} - <span class="{status_class}">{status_text}</span></h2>
        <div class="times">Execution: {res['execution_time']:.2f}s | Validation: {res['validation_time']:.2f}s</div>
        
        <h3>Response</h3>
        <pre>{res['response']}</pre>
        
        <h3>Validation Details</h3>
        <pre>{res['validation_reasoning']}</pre>
    </div>
"""
    html += "</body></html>"
    out_path.write_text(html, encoding="utf-8")
    print(f"\nReport generated: {out_path.absolute()}")

def main():
    parser = argparse.ArgumentParser(description="Run AI Workflow step tests via CLI.")
    parser.add_argument("--workflow", required=True, help="Workflow ID")
    parser.add_argument("--step", required=True, help="Step ID")
    parser.add_argument("--test-case", help="Specific test case to run. If omitted, runs all.")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    args = parser.parse_args()

    step_dir = Path(args.project_root) / ".ai-workflows" / args.workflow / "fixtures" / args.step
    if not step_dir.exists():
        print(f"Error: Step fixtures directory not found: {step_dir}")
        return

    test_cases = []
    if args.test_case:
        test_cases = [args.test_case]
    else:
        test_cases = [d.name for d in step_dir.iterdir() if d.is_dir()]

    if not test_cases:
        print(f"No test cases found for step {args.step}")
        return

    results = []
    for tc in test_cases:
        print(f"\n--- Running: {tc} ---")
        res = execute_test_case(args.workflow, args.step, tc, args.project_root)
        results.append(res)
        if res.get('passed'):
            print("Status: PASS")
        elif res.get('status') == 'error':
            print(f"Status: ERROR ({res.get('message')})")
        else:
            print("Status: FAIL")

    report_path = Path(args.project_root) / f"debug_report_{args.workflow}_{args.step}.html"
    generate_html_report(args.workflow, args.step, results, report_path)

if __name__ == "__main__":
    main()
