# Flexible Contract Model

Contracts in this skill are intentionally more flexible than rigid JSON-only schemas.

## Goal

Allow each step to declare what counts as valid input and output without forcing every artifact into a single structural format.

## Contract layers

Each step can define validation at one or more layers:

### 1. Structural validation

Use this when the output is machine-readable and shape matters.

Examples:

- JSON object must include `summary` and `decision`
- Markdown must contain `## Risks`
- A file path must exist after the step finishes

### 2. Semantic validation

Use this when the output may be free-form but still must satisfy meaning-based rules.

Examples:

- output must answer the user's request directly
- output must mention blockers if any exist
- plan must include at least one next action
- PRD section must be internally consistent with previous context

### 3. Side-effect validation

Use this when success is defined by something written or changed.

Examples:

- artifact file created
- run state updated with a specific field
- snapshot captured

## Recommended contract block

Put the machine-readable block in the step file under `## Machine Contract`.

```json
{
  "step_id": "step-02-plan",
  "inputs_required": ["normalized_request"],
  "outputs_written": ["plan_markdown"],
  "validation": {
    "input": [
      {
        "kind": "presence",
        "target": "normalized_request"
      }
    ],
    "output": [
      {
        "kind": "markdown_contains_headings",
        "target": "plan_markdown",
        "headings": ["## Goals", "## Risks", "## Next Actions"]
      },
      {
        "kind": "semantic_rule",
        "target": "plan_markdown",
        "rule": "The plan must include at least one concrete next action and mention blockers if confidence is low."
      }
    ],
    "side_effects": [
      {
        "kind": "artifact_exists",
        "path": "runs/<run-id>/artifacts/step-02-plan.output.json"
      }
    ]
  },
  "recommended_next_step": "step-03-draft"
}
```

## Current state of the runtime

Right now the runtime driver understands routing and state progression directly.

Validation support is currently at the contract-definition level:

- the skill and templates support flexible validation declarations
- the runtime does not yet execute every semantic rule automatically

So today:

- structural and semantic validation can be documented and followed by the agent
- fully automatic rule evaluation still needs a dedicated validator pass

This is deliberate. It keeps the workflow expressive while avoiding fake certainty from overly rigid JSON-only checks.
