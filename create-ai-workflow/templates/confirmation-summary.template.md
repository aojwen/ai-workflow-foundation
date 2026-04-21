# Workflow Confirmation Summary

Use this exact structure before creation. Ensure every step's Goal, Inputs, and Outputs are clearly discovered.

```md
**Proposed Workflow**

`workflow_id`: <workflow-id>
`goal`: <one-sentence goal>
`target_dir`: <resolved directory>
`routing_strategy`: Step-driven (via nextStep) with Main Agent orchestration

**Step-by-Step Breakdown**

1. **<step-id-01>**: <Step Goal>
   - **Inputs**: 
     - **workDir**: `runs/<workflow-id>/<run-id>/<step-id>/`
     - <Other dynamic context>
   - **Recommend Next Step**: <Logic for calculating the next transition>
   - **Output**: <Flat JSON fields + schema reference>
   - **Success Criteria**: <Criteria for acceptance>

2. **<step-id-02>**: <Step Goal>
   - **Inputs**: 
     - **workDir**: `runs/<workflow-id>/<run-id>/<step-id>/`
     - <Other dynamic context>
   - **Recommend Next Step**: <Logic for calculating the next transition>
   - **Output**: <Flat JSON fields + schema reference>
   - **Success Criteria**: <Criteria for acceptance>

**State Management**
- **state.md**: Uses frontmatter ONLY for progress tracking and a descriptive body for complete step outcomes (fields, values, and explanations).

**Standardized Steps**
Each step prompt will strictly follow the structure: **Step Goal, Input, Instructions, Recommend Next Step, Output, Success/Failure Criteria**.

**Directory Structure**
- `steps/schemas/`: Contains JSON schemas for every step output.
- `runs/<workflow-id>/<run-id>/<step-id>/`: Isolated execution folder for each step's prompt, response, and artifacts. `workDir` is injected into the sub-agent.

Reply with `确认创建` if this plan looks right, and I’ll generate it automatically.
```
