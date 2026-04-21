---
name: create-ai-workflow
description: Guided creation of isolated, step-based AI workflows. Use this skill to design a new workflow, identify its steps, and scaffold the necessary file structure including Markdown-based test fixtures.
---

# Create AI Workflow

Use this skill to design and scaffold a new AI workflow. This skill follows an orchestration model where a main agent manages routing and state, while specialized sub-agents execute individual steps.

## Design Principles

- **Main Agent Orchestration:** The main agent is responsible for coordination, routing, generating a unique `run-id` (e.g., timestamp-based), and updating the global run state in `state.md`.
- **Sub-Agent Execution:** Every workflow step MUST be executed by a sub-agent. The sub-agent calculates the next step but the main agent performs the actual transition.
- **Strict Step Structure:** Each step prompt must follow a standardized structure: Step Goal, Input, Instructions, Recommend Next Step, Output, Success/Failure Criteria.
- **Workspace Isolation:** Every step execution must have its own working directory: `runs/<workflow-id>/<run-id>/<step-id>/`. The path MUST be passed as `workDir` to the sub-agent.
- **Schema-Based Outputs:** Every step must define a JSON schema for its output. Outputs are flat JSON containing only workflow indicators and paths to complex artifacts.
- **Markdown State:** The run state is maintained in `state.md`. Use frontmatter ONLY for progress tracking. Record complete step outcomes (including field descriptions) in the body.

## When to use

- You need to create a new AI workflow from scratch.
- You want to refactor a complex task into a structured, multi-step workflow.
- You want to transform an existing workflow into this structured format while preserving its context and reference documents.
- You need to define clear contracts and test cases for an agentic process.

## Workflow Creation Process

### 1. Discovery (Pre-initialization)
Before writing any files, you MUST clarify all necessary details with the user:
- **Workflow Identity:** A clear name and unique ID (slug).
- **Goal:** The ultimate objective of the workflow.
- **Steps:** A complete list of steps.
- **Step Details:** For EACH step, define:
  - **Step Goal:** Specific task for this step.
  - **Input:** Dynamic context needed, including the mandatory `workDir`.
  - **Recommend Next Step:** How this step suggests the next transition.
  - **Output:** Flat JSON structure + JSON Schema file.
  - **Success/Failure Criteria:** Acceptance standards.

### 2. Refactoring/Transformation Guidelines
When transforming an existing workflow or design:
- **No Information Loss:** DO NOT aggressively compress or omit information from the original workflow. Ensure all business logic and edge cases are preserved in the new `Instructions` sections.
- **Reference Migration:** If the original workflow references external documents, guides, or examples, migrate these to the new workflow's `references/` directory or embed them directly into the relevant `steps/` if small.
- **Asset Preservation:** Ensure any non-code assets (prompts, data samples) are kept and correctly paths are updated.

### 3. Confirmation Summary
Present a structured plan to the user for approval. Use the `templates/confirmation-summary.template.md` format.

### 4. Scaffolding (Post-confirmation)
Once confirmed, generate the workflow structure:
- `orchestration.md`: The source of truth for routing.
- `steps/step-NN-<name>.md`: Standardized instruction sets for sub-agents.
- `steps/schemas/step-NN-<name>.schema.json`: Output schema for the step.
- `fixtures/<step-id>/<test-case-name>/`: Markdown-based test cases.

## Standard Directory Layout

```text
.ai-workflows/<workflow-id>/
  orchestration.md          # Main agent's routing logic
  workflow.spec.json        # Metadata about the workflow
  references/               # Migrated reference documents and guides
  steps/
    step-01-discovery.md    # Standardized instructions
    step-02-processing.md
    schemas/
      step-01-discovery.schema.json
  fixtures/
    step-01-discovery/
      happy-path/
        prompt.md           # Input to sub-agent
        expected.md         # Descriptive expectation
        assertions.md       # Markdown criteria for main agent
  runs/                     # Directory for execution state (example/gitkeep)
```

## Step Prompt Structure

Each step file in `steps/` MUST follow this standardized structure.

```markdown
# Step: <step-id>

## Step Goal
<Specific task definition for this step>

## Input
<List of required dynamic context with descriptions>
- **workDir**: The absolute path to the working directory for this step (`runs/<workflow-id>/<run-id>/<step-id>/`).
- **<Input Name>**: <Description>

## Instructions
<The core "how-to". Detailed business logic, execution rules, and steps the sub-agent must follow. Reference any documents in `references/` if applicable.>

## Recommend Next Step
<Logic to determine the next step ID>

## Output
<Flat JSON structure reference>
- **JSON Schema**: `steps/schemas/<step-id>.schema.json`
- **Fields**:
  - `success`: (Boolean) True if Success Criteria are met.
  - `nextStep`: The ID of the next step.
  - `schema`: Path to the JSON schema.
  - <other-business-fields>

## Success/Failure Criteria
<Standards for completion. The sub-agent evaluates these to set the 'success' boolean.>
```
