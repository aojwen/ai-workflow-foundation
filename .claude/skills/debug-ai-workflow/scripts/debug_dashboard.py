#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
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
Ensure the sub-agent correctly followed the Workspace Instructions, provided a valid 'success' boolean, and emitted 'nextSteps' as an array.

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
    
    if not fixture_dir.exists():
        return {"error": "Fixture not found"}
        
    prompt_content = (fixture_dir / "prompt.md").read_text(encoding="utf-8")
    expected_content = (fixture_dir / "expected.md").read_text(encoding="utf-8") if (fixture_dir / "expected.md").exists() else ""
    assertions_content = (fixture_dir / "assertions.md").read_text(encoding="utf-8") if (fixture_dir / "assertions.md").exists() else ""

    import datetime
    run_id = datetime.datetime.now().strftime("run-%Y%m%d-%H%M%S")
    debug_run_dir = base_project / "debugs" / workflow_id / step_id / test_case / run_id
    debug_run_dir.mkdir(parents=True, exist_ok=True)
    
    workspace_path_str = str(debug_run_dir.absolute())
    resolved_prompt = prompt_content.replace("{workDir}", workspace_path_str)

    final_prompt = DEBUG_EXECUTION_WRAPPER.format(
        workspace_dir=workspace_path_str, 
        step_prompt=resolved_prompt
    )
    
    start_time = time.time()
    response = run_claude(final_prompt, project_root)
    exec_time = time.time() - start_time

    val_prompt = DEBUG_VALIDATION_PROMPT.format(expected_content=expected_content, assertions_content=assertions_content, response=response)
    
    val_start = time.time()
    val_response = run_claude(val_prompt, project_root)
    val_time = time.time() - val_start

    passed = "RESULT_PASS" in val_response
    
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

class DebugHandler(SimpleHTTPRequestHandler):
    project_root = "."

    def do_GET(self):
        if self.path == "/api/workflows":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            workflows_dir = Path(self.project_root).expanduser() / ".ai-workflows"
            workflows = []
            if workflows_dir.exists():
                for wf in workflows_dir.iterdir():
                    if wf.is_dir():
                        steps = []
                        fixtures_dir = wf / "fixtures"
                        if fixtures_dir.exists():
                            for step in fixtures_dir.iterdir():
                                if step.is_dir():
                                    test_cases = [tc.name for tc in step.iterdir() if tc.is_dir()]
                                    steps.append({"id": step.name, "test_cases": test_cases})
                        workflows.append({"id": wf.name, "steps": steps})
            
            self.wfile.write(json.dumps(workflows).encode())
            return
            
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/run":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data)
            
            result = execute_test_case(req['workflow'], req['step'], req['test_case'], self.project_root)
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return

        self.send_response(404)
        self.end_headers()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    DebugHandler.project_root = args.project_root
    
    dashboard_dir = Path(__file__).parent.parent / "dashboard"
    os.chdir(dashboard_dir)
    
    server = HTTPServer(('localhost', args.port), DebugHandler)
    url = f"http://localhost:{args.port}"
    print(f"Starting Debug Dashboard at {url}")
    print(f"Project Root: {Path(args.project_root).resolve()}")
    
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard...")
        server.server_close()

if __name__ == "__main__":
    main()
