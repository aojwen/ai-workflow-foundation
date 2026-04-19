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

# Re-use execution logic from CLI script
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
    base_dir = Path(project_root) / ".ai-workflows" / workflow_id / "fixtures" / step_id / test_case

    # Support both prompt.md and input.md
    prompt_file = base_dir / "input.md" if (base_dir / "input.md").exists() else base_dir / "prompt.md"
    expected_file = base_dir / "expected.md"
    assertions_file = base_dir / "assertions.md"

    if not prompt_file.exists():
        return {"status": "error", "message": f"Prompt file not found: {prompt_file}"}

    prompt_content = prompt_file.read_text(encoding="utf-8")
    expected_content = expected_file.read_text(encoding="utf-8") if expected_file.exists() else ""
    assertions_content = assertions_file.read_text(encoding="utf-8") if assertions_file.exists() else ""

    start_time = time.time()
    response = run_claude(prompt_content, project_root)
    exec_time = time.time() - start_time

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
    validation_response = run_claude(validation_prompt, project_root)
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

class DebugHandler(SimpleHTTPRequestHandler):
    project_root = "."
    dashboard_dir = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.dashboard_dir, **kwargs)

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
            # Serve static files from dashboard_dir
            super().do_GET()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/run':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            workflow = data.get('workflow')
            step = data.get('step')
            test_case = data.get('test_case')
            
            result = execute_test_case(workflow, step, test_case, self.project_root)
            self.send_json(result)
        else:
            self.send_error(404, "Endpoint not found")

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def get_workflows(self):
        base = Path(self.project_root) / ".ai-workflows"
        if not base.exists():
            return []
        return [d.name for d in base.iterdir() if d.is_dir()]

    def get_steps(self, workflow):
        if not workflow: return []
        base = Path(self.project_root) / ".ai-workflows" / workflow / "fixtures"
        if not base.exists():
            return []
        return sorted([d.name for d in base.iterdir() if d.is_dir()])

    def get_test_cases(self, workflow, step):
        if not workflow or not step: return []
        base = Path(self.project_root) / ".ai-workflows" / workflow / "fixtures" / step
        if not base.exists():
            return []
        return sorted([d.name for d in base.iterdir() if d.is_dir()])

    def get_fixtures(self, workflow, step, test_case):
        if not workflow or not step or not test_case:
            return {"prompt": "", "expected": "", "assertions": ""}

        base = Path(self.project_root) / ".ai-workflows" / workflow / "fixtures" / step / test_case

        # Support both prompt.md and input.md
        prompt_file = base / "input.md" if (base / "input.md").exists() else base / "prompt.md"
        expected_file = base / "expected.md"
        assertions_file = base / "assertions.md"

        return {
            "prompt": prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else "",
            "expected": expected_file.read_text(encoding="utf-8") if expected_file.exists() else "",
            "assertions": assertions_file.read_text(encoding="utf-8") if assertions_file.exists() else ""
        }

def main():
    parser = argparse.ArgumentParser(description="Start Debug Dashboard Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to run on")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    args = parser.parse_args()

    # Determine dashboard directory relative to this script
    script_dir = Path(__file__).parent.absolute()
    dashboard_dir = script_dir.parent / "dashboard"

    DebugHandler.project_root = args.project_root
    DebugHandler.dashboard_dir = str(dashboard_dir)

    server_address = ('', args.port)
    httpd = HTTPServer(server_address, DebugHandler)
    
    url = f"http://localhost:{args.port}"
    print(f"Starting Debug Dashboard at {url}")
    print(f"Project root: {Path(args.project_root).absolute()}")
    webbrowser.open(url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    main()
