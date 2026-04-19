---
name: debug-ai-workflow
description: Isolated debugging and testing of AI workflow steps. Use this skill to run individual steps against Markdown-based test fixtures and validate their behavior.
---

# Debug AI Workflow

Use this skill to debug individual steps of an AI workflow in isolation. This skill leverages Markdown-based test fixtures to provide repeatable and descriptive testing.

## Design Principles

- **Isolation:** Debug exactly one step at a time without affecting the main run state.
- **Markdown Fixtures:** Use human-readable Markdown files for prompts, expected outputs, and assertions.
- **Agent Execution:** The scripts use the `claude -p` CLI command to execute the sub-agent and perform assertions.

## Execution Modes

As the executing agent, **you are responsible for invoking the underlying scripts automatically**. The user should only need to state their intent (e.g., "Debug step 2 of workflow X" or "Open the debug dashboard").

### 1. CLI Mode (Default Behavior)
If the user asks to debug a workflow or step without specifying a mode, default to this batch execution.
- **Agent Action:** You call `run_shell_command` with `scripts/debug_cli.py --workflow <workflow-id> --step <step-id> [--test-case <test-case>] --project-root <root>`.
- **Behavior:**
  - If a specific test case isn't mentioned, run all test cases for that step.
  - Read the results from the CLI output and summarize them for the user.
  - The script internally uses `claude -p` to execute and validate, generating an HTML report.

### 2. Interactive Mode (Dashboard)
If the user explicitly asks for the "dashboard", "UI", or "interactive mode".
- **Agent Action:** You call `run_shell_command` with `scripts/debug_dashboard.py --project-root <root>`. **CRITICAL: You MUST set `is_background: true`** because this script starts a long-running web server.
- **Behavior:**
  - The script will automatically open the user's default web browser to the dashboard.
  - The user can select workflows, steps, and test cases visually.
  - Clicking "Run Test" in the UI triggers the `claude -p` logic.
  - The agent should inform the user that the dashboard is running in the background and they can interact with it in their browser.

## Debug Artifacts (Logging)

Regardless of the execution mode used (CLI or Dashboard), the results of every debug execution are permanently recorded in the project root under the `debugs/` directory.

**Directory Structure:**
```text
debugs/
  <workflow-id>/
    <step-id>/
      <test-case>/
        response.md       # The raw output from the sub-agent
        validation.md     # The validation reasoning and decision
        result.json       # Execution metadata (time, status, etc.)
```

## Fixture Structure

- `fixtures/<step-id>/<test-case>/prompt.md`: The exact prompt provided to the sub-agent.
- `fixtures/<step-id>/<test-case>/expected.md`: A descriptive summary of what the output should look like.
- `fixtures/<step-id>/<test-case>/assertions.md`: Markdown-based success criteria for the validation agent.
