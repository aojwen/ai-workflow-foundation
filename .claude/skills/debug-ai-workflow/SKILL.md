---
name: debug-ai-workflow
description: Isolated debugging and testing of AI workflow steps. Use this skill to run individual steps against Markdown-based test fixtures and validate their behavior.
---

# Debug AI Workflow

Use this skill to debug individual steps of an AI workflow in isolation. This skill leverages Markdown-based test fixtures to provide repeatable and descriptive testing.

## Design Principles

- **Isolation:** Debug exactly one step at a time without affecting the main execution `runs/` directory.
- **Markdown Fixtures:** Use human-readable Markdown files for prompts, expected outputs, and assertions.
- **Step Contracts:** Debugging tests whether the step correctly executes its `Instructions`, outputs a flat JSON matching its `schema` (including globally unique custom variables), correctly evaluates its own `success` boolean, and emits a valid `nextSteps` array for DAG routing.
- **Workspace Injection:** The debugging environment injects a temporary `{workDir}` into the sub-agent prompt and ensures artifacts are saved properly to that directory.

## Execution Modes

As the executing agent, **you are responsible for invoking the underlying scripts automatically**. The user should only need to state their intent (e.g., "Debug step 2 of workflow X" or "Open the debug dashboard").

### 1. CLI Mode (Default Behavior)
If the user asks to debug a workflow or step without specifying a mode, default to this batch execution.
- **Agent Action:** You call `run_shell_command` with `scripts/debug_cli.py --workflow <workflow-id> --step <step-id> [--test-case <test-case>] --project-root <root>`.
- **Behavior:**
  - If a specific test case isn't mentioned, run all test cases for that step.
  - Read the results from the CLI output and summarize them for the user.
  - The script validates the sub-agent's JSON output (including the `success` field and `nextSteps` array) against the `assertions.md`.

### 2. Interactive Mode (Dashboard)
If the user explicitly asks for the "dashboard", "UI", or "interactive mode".
- **Agent Action:** You call `run_shell_command` with `scripts/debug_dashboard.py --project-root <root>`. **CRITICAL: You MUST set `is_background: true`** because this script starts a long-running web server.
- **Behavior:**
  - The script will automatically open the user's default web browser to the dashboard.
  - The user can select workflows, steps, and test cases visually.
  - Clicking "Run Test" in the UI triggers the test logic.

## Directory Structure (Project Root)

All debugging execution results live in the `debugs/` folder at the root of the project, while definitions remain in `.ai-workflows/`.

```text
.ai-workflows/
  <workflow-id>/
    fixtures/
      <step-id>/
        <test-case>/
          prompt.md         # Static Definition (Supports {workDir} placeholder)
          expected.md       # Static Definition
          assertions.md     # Static Definition

debugs/                     <-- Execution Outputs
  <workflow-id>/
    <step-id>/
      <test-case>/
        <run-id>/           <-- Isolated Debug Run (Timestamp)
          sub-agent-prompt.md # The composite prompt sent to sub-agent
          response.json     # The raw flat JSON output
          validation.md     # The orchestrator's validation reasoning
          result.json       # Metadata (pass/fail, time)
          <artifacts>       # Any files generated during this debug run
```
