# Step Handoff Packet Protocol

Use this protocol whenever the main agent delegates a normal workflow step to a child agent.

## Core rule

No normal workflow step should be executed before the main agent prepares a handoff packet.

This packet is the execution boundary between:

- main-agent orchestration work
- child-agent step execution work

## Purpose

The packet exists to:

- keep child-agent context minimal
- prevent the main agent from silently doing step business work itself
- make step execution reproducible
- preserve routing discipline

## Required fields

- `workflow_id`
- `run_id`
- `step_id`
- `step_file`
- `step_purpose`
- `inputs_required`
- `provided_inputs`
- `relevant_prior_outputs`
- `relevant_references`
- `expected_output_contract`
- `return_format`
- `routing_reminder`

## Recommended fields

- `user_prompt`
- `constraints`
- `debug_context`
- `submission_target`

## Routing reminder

Every packet should remind the child agent:

- it is executing one step only
- it does not own routing
- `recommended_next_step` is only a hint
- the main agent will decide what happens next

## Packet assembly rules

The main agent should:

1. read the current step contract
2. include only the required inputs
3. include only the references relevant to this step
4. include only the prior outputs needed by this step
5. exclude unrelated workflow history

## Return rules

The child agent should return:

- `step_id`
- `business_output`
- `routing_relevant_findings`
- `recommended_next_step`
- `blockers`

The main agent then validates the return and updates run state.

## Exception policy

If the main agent executes a normal step without producing a handoff packet first, that should be treated as an exception and recorded in run state.
