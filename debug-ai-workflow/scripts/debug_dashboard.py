#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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

    prompt_content = (fixture_dir / "prompt.md").read_text(encoding="utf-8")
    expected_content = (fixture_dir / "expected.md").read_text(encoding="utf-8") if (fixture_dir / "expected.md").exists() else ""
    assertions_content = (fixture_dir / "assertions.md").read_text(encoding="utf-8") if (fixture_dir / "assertions.md").exists() else ""

    # Setup isolated run directory: debugs/<workflow-id>/<step-id>/<test-case>/<run-id>/
    import datetime
    run_id = datetime.datetime.now().strftime("run-%Y%m%d-%H%M%S")
    debug_run_dir = base_project / "debugs" / workflow_id / step_id / test_case / run_id
    debug_run_dir.mkdir(parents=True, exist_ok=True)

    final_prompt = DEBUG_EXECUTION_WRAPPER.format(workspace_dir=debug_run_dir.absolute(), step_prompt=prompt_content)
    
    start_time = time.time()
    response = run_claude(final_prompt, project_root)
    exec_time = time.time() - start_time

    val_prompt = DEBUG_VALIDATION_PROMPT.format(expected_content=expected_content, assertions_content=assertions_content, response=response)
    val_response = run_claude(val_prompt, project_root)
    passed = "RESULT_PASS" in val_response
    
    (debug_run_dir / "sub-agent-prompt.md").write_text(final_prompt, encoding="utf-8")
    (debug_run_dir / "response.json").write_text(response, encoding="utf-8")
    (debug_run_dir / "validation.md").write_text(val_response, encoding="utf-8")
    
    return {"passed": passed, "execution_time": exec_time, "workspace": str(debug_run_dir)}

class DebugHandler(SimpleHTTPRequestHandler):
    project_root = "."
    dashboard_dir = ""

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/workflows':
            self.send_json(self.get_workflows())
        elif parsed_path.path == '/api/steps':
            query = parse_qs(parsed_path.query)
            workflow = query.get('workflow', [''])[0]
            self.send_json(self.get_steps(workflow))
        elif parsed_path.path == '/api/test-cases':
            query = parse_qs(parsed_path.query)
            workflow = query.get('workflow', [''])[0]
            step = query.get('step', [''])[0]
            self.send_json(self.get_test_cases(workflow, step))
        elif parsed_path.path == '/api/fixtures':
            query = parse_qs(parsed_path.query)
            workflow = query.get('workflow', [''])[0]
            step = query.get('step', [''])[0]
            test_case = query.get('test_case', [''])[0]
            self.send_json(self.get_fixtures(workflow, step, test_case))
        else:
            # Serve static files from dashboard directory
            os.chdir(self.dashboard_dir)
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/run':
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            result = execute_test_case(data['workflow'], data['step'], data['test_case'], self.project_root)
            self.send_json(result)

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def get_workflows(self):
        base = Path(self.project_root) / ".ai-workflows"
        return [d.name for d in base.iterdir() if d.is_dir()] if base.exists() else []

    def get_steps(self, workflow):
        base = Path(self.project_root) / ".ai-workflows" / workflow / "fixtures"
        return sorted([d.name for d in base.iterdir() if d.is_dir()]) if base.exists() else []

    def get_test_cases(self, workflow, step):
        base = Path(self.project_root) / ".ai-workflows" / workflow / "fixtures" / step
        return sorted([d.name for d in base.iterdir() if d.is_dir()]) if base.exists() else []

    def get_fixtures(self, workflow, step, test_case):
        base = Path(self.project_root) / ".ai-workflows" / workflow / "fixtures" / step / test_case
        return {
            "prompt": (base / "prompt.md").read_text(encoding="utf-8") if (base / "prompt.md").exists() else "",
            "expected": (base / "expected.md").read_text(encoding="utf-8") if (base / "expected.md").exists() else "",
            "assertions": (base / "assertions.md").read_text(encoding="utf-8") if (base / "assertions.md").exists() else ""
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    script_dir = Path(__file__).parent.absolute()
    DebugHandler.project_root = args.project_root
    DebugHandler.dashboard_dir = str(script_dir.parent / "dashboard")

    os.chdir(DebugHandler.dashboard_dir)
    httpd = HTTPServer(('', args.port), DebugHandler)
    webbrowser.open(f"http://localhost:{args.port}")
    print(f"Dashboard serving from: {DebugHandler.dashboard_dir}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()
