# Workflow Confirmation Summary

Use this exact structure before creation. Ensure every step's task, inputs, and outputs are clearly discovered.

```md
**Proposed Workflow**

`workflow_id`: <workflow-id>
`goal`: <one-sentence goal>
`target_dir`: <resolved directory>
`routing_strategy`: <Sequential / Describe custom conditional routing>

**Step-by-Step Breakdown**

1. **<step-id-01>**: <Task description>
   - **Inputs**: <List of required inputs>
   - **Outputs**: <List of produced outputs>
2. **<step-id-02>**: <Task description>
   - **Inputs**: <List of required inputs>
   - **Outputs**: <List of produced outputs>

**Test Fixtures**

We will generate Markdown-based fixtures for each step under `fixtures/<step-id>/happy-path/`:
- `prompt.md`: The exact prompt to be sent to the sub-agent.
- `expected.md`: Descriptive expectation of the result.
- `assertions.md`: Human-readable criteria for validation.

**Orchestration Model**
- **Main Agent**: Responsible for coordination, routing, and updating global run state.
- **Sub-Agents**: MUST perform the business logic for every step.

Reply with `确认创建` if this plan looks right, and I’ll generate it automatically.
```
