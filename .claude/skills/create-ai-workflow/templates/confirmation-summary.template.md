# Workflow Confirmation Summary

Use this exact structure before creation. Ensure every step's Goal, Inputs, and Outputs are clearly discovered.

```md
**Proposed Workflow**

`workflow_id`: <workflow-id>
`goal`: <one-sentence goal>
`target_dir`: <resolved directory>
`routing_strategy`: Reactive Admission Control (Deterministic DAG via `routing.json`)

**Step-by-Step Breakdown**

1. **<step-id-01>**: <Step Goal>
   - **Admission Conditions**: 
     - **depends_on**: [<list of steps>]
     - **required_inputs**: { "path.to.key": "expected_value" }
   - **Inputs**: 
     - **workDir**: `runs/<workflow-id>/<run-id>/<step-id>/`
     - <Other dynamic context>
   - **Recommend Next Steps**: <Next steps to signal upon completion>
   - **Output**: <Flat JSON fields (Globally Unique) + schema reference>
   - **Success Criteria**: <Criteria for acceptance>

2. **<step-id-02>**: <Step Goal>
   ... (repeat for all steps)

**State Management**
- **state.md**: Uses frontmatter for the reactive state machine (`active_steps`, `completed_steps`, `pending_signals`) and a descriptive body for complete step outcomes.
- **routing.json**: Standalone JSON defining admission pre-conditions (OR/AND logic) for each step, decoupled from the LLM prompt.

**Standardized Steps**
Each step prompt will strictly follow the structure: **Step Goal, Input, Instructions, Recommend Next Steps (Array), Output, Success/Failure Criteria**.

**Directory Structure**
- `routing.json`: Deterministic routing logic.
- `steps/schemas/`: JSON schemas for every step output.
- `runs/<workflow-id>/<run-id>/<step-id>/`: Isolated execution folder. `workDir` is injected into the sub-agent.

**Global Integrity**
- Output variable names are verified to be globally unique across all steps to prevent state collisions.

Reply with `确认创建` if this plan looks right, and I’ll generate it automatically.
```
