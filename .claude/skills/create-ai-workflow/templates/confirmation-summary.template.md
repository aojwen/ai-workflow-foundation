# Workflow Confirmation Summary

Use this exact structure before creation. Ensure every step's Goal, Inputs, and Outputs are clearly discovered.

```md
**Proposed Workflow**

`workflow_id`: <workflow-id>
`goal`: <one-sentence goal>
`target_dir`: <resolved directory>
`routing_strategy`: Reactive DAG (depends_on + required_inputs) with Main Agent orchestration

**Step-by-Step Breakdown**

1. **<step-id-01>**: <Step Goal>
   - **Inputs**: 
     - **workDir**: `runs/<workflow-id>/<run-id>/<step-id>/`
     - <Other dynamic context>
   - **Recommend Next Steps**: <Logic for calculating next transition(s), returned as an array>
   - **Output**: <Flat JSON fields (must be globally unique) + schema reference>
   - **Success Criteria**: <Criteria for acceptance>

2. **<step-id-02>**: <Step Goal>
   - **Inputs**: 
     - **workDir**: `runs/<workflow-id>/<run-id>/<step-id>/`
     - <Other dynamic context>
   - **Recommend Next Steps**: <Logic for calculating next transition(s), returned as an array>
   - **Output**: <Flat JSON fields (must be globally unique) + schema reference>
   - **Success Criteria**: <Criteria for acceptance>

**State Management**
- **state.md**: Uses frontmatter for the reactive state machine (`active_steps`, `completed_steps`, `pending_signals`) and a descriptive body for complete step outcomes (fields, values, and explanations).

**Standardized Steps**
Each step prompt will strictly follow the structure: **Step Goal, Input, Instructions, Recommend Next Steps, Output, Success/Failure Criteria**.

**Directory Structure**
- `steps/schemas/`: Contains JSON schemas for every step output.
- `runs/<workflow-id>/<run-id>/<step-id>/`: Isolated execution folder for each step's prompt, response, and artifacts. `workDir` is injected into the sub-agent.

Reply with `确认创建` if this plan looks right, and I’ll generate it automatically.
```
