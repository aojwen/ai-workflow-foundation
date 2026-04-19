---
name: create-ai-workflow
description: Guided creation of isolated, step-based AI workflows. Use this skill to design a new workflow, identify its steps, and scaffold the necessary file structure including Markdown-based test fixtures.
---

# Create AI Workflow

Use this skill to design and scaffold a new AI workflow. This skill follows an orchestration model where a main agent manages routing and state, while specialized sub-agents execute individual steps.

## Design Principles

- **Main Agent Orchestration:** The main agent is responsible for coordination, routing, and updating the global run state.
- **Sub-Agent Execution:** Every workflow step MUST be executed by a sub-agent. The main agent must not perform the business logic of a step.
- **Isolation:** Each step is an independent unit with defined inputs and outputs.
- **Markdown Fixtures:** Debugging and testing are powered by Markdown files in a nested structure, prioritizing descriptive assertions over strict JSON validation.

## When to use

- You need to create a new AI workflow from scratch.
- You want to refactor a complex task into a structured, multi-step workflow.
- You need to define clear contracts and test cases for an agentic process.

## Workflow Creation Process

### 1. Discovery (Pre-initialization)
Before writing any files, you MUST clarify all necessary details with the user:
- **Workflow Identity:** A clear name and unique ID (slug).
- **Goal:** The ultimate objective of the workflow.
- **Steps:** A complete list of steps in the sequence.
- **Routing & Transitions:** How do the steps connect? Are there conditional branches, loops, or error-handling paths? **If this is unclear, you MUST ask the user. If the user does not provide a clear answer, default to linear sequential execution.**
- **Step Details:** For EACH step, you must understand:
  - The specific task/mission.
  - The required inputs (what data is needed from previous steps or the user).
  - The expected outputs (what this step produces for the next step or final result).

### 2. Confirmation Summary
Present a structured plan to the user for approval. Include:
- Workflow ID and Goal.
- Target directory.
- Detailed step-by-step breakdown (Task, Inputs, Outputs).
- Proposed test cases for each step.

### 3. Scaffolding (Post-confirmation)
Once confirmed, generate the workflow structure:
- `orchestration.md`: The source of truth for routing and state management.
- `steps/step-NN-<name>.md`: Isolated instruction sets for sub-agents.
- `fixtures/<step-id>/<test-case-name>/`: Markdown-based test cases.
  - `prompt.md`: The exact prompt to be sent to the sub-agent.
  - `expected.md`: Descriptive expectation of the result.
  - `assertions.md`: Human-readable criteria for the main agent to judge success.

## Standard Directory Layout

```text
.ai-workflows/<workflow-id>/
  orchestration.md          # Main agent's routing logic
  workflow.spec.json        # Metadata about the workflow
  steps/
    step-01-discovery.md    # Instructions for sub-agent
    step-02-processing.md
  fixtures/
    step-01-discovery/
      happy-path/
        prompt.md           # Input to sub-agent
        expected.md         # Descriptive expectation
        assertions.md       # Markdown criteria for main agent
  runs/                     # Directory for execution state
  snapshots/                # Captured states for debugging
```

## Recommended Tools

- Use `scripts/create_workflow.py` to automate the file generation after the spec is finalized and confirmed.
