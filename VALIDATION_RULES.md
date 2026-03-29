# Validation Rules

## Purpose

This document defines the shared validation rule set for WHRS ORC.

Validation must protect:
- physical correctness
- solver stability
- result interpretability
- safe reporting

## Validation philosophy

- Validate before solve when possible.
- Validate after solve for physical consistency and closure.
- Block non-physical results.
- Warn on borderline or assumption-heavy results.
- Never silently auto-correct a dangerous engineering input.

## Validation actions

Supported actions:
- `block`
- `hard_warning`
- `soft_warning`
- `info`

Rules:
- `block` stops the equipment solve and returns a structured blocked result.
- `hard_warning` allows a result but marks it as requiring user attention.
- `soft_warning` informs the user without rejecting the solve.

## Tolerance policy

Default tolerances should be configurable, but the first planning basis should assume:
- composition sum tolerance: `1e-4`
- energy closure default threshold: project-configurable
- positive temperature approach minimum: strictly greater than `0 K`
- reported pinch default warning threshold: project-configurable

## Rule groups

### Group A - Input integrity

#### `VAL-COMP-001`
- Scope: mixture definitions
- Rule: composition fractions must sum to `1.0 +/- tolerance`
- Action: `block`

#### `VAL-FLOW-001`
- Scope: all streams
- Rule: mass flow must be strictly positive
- Action: `block`

#### `VAL-PRES-001`
- Scope: all pressured states
- Rule: pressure must be positive
- Action: `block`

#### `VAL-TEMP-001`
- Scope: all temperature inputs
- Rule: temperature must be above absolute zero and within configured fluid limits when defined
- Action: `block`

### Group B - Hot/cold-side consistency

#### `VAL-HX-001`
- Scope: heat-exchange blocks
- Rule: hot-side inlet temperature must exceed hot-side outlet temperature when cooling is expected
- Action: `block`

#### `VAL-HX-002`
- Scope: heat-exchange blocks
- Rule: cold-side outlet temperature must exceed cold-side inlet temperature when heating is expected
- Action: `block`

#### `VAL-HX-003`
- Scope: heat-exchange blocks
- Rule: minimum pinch or approach temperature must remain greater than zero
- Action: `block`

### Group C - Exhaust and boiler safeguards

#### `VAL-STACK-001`
- Scope: exhaust source and boiler
- Rule: resolved stack temperature must not fall below the configured minimum stack temperature
- Action: `block`

#### `VAL-BOILER-001`
- Scope: waste heat boiler
- Rule: absorbed oil heat must not exceed physically available exhaust heat
- Action: `block`

#### `VAL-BOILER-002`
- Scope: waste heat boiler
- Rule: boiler closure ratio beyond configured threshold must trigger visibility
- Action: `hard_warning` or `block`, depending on severity

#### `VAL-BOILER-003`
- Scope: waste heat boiler design mode
- Rule: one and only one governing design driver must be selected when design mode is used
- Action: `block`

#### `VAL-BOILER-004`
- Scope: waste heat boiler design mode
- Rule: the selected design driver must include its required target value
- Action: `block`

#### `VAL-BOILER-005`
- Scope: waste heat boiler design mode
- Rule: if the chosen design driver does not define a unique physical solution with the entered inputs, block the solve
- Action: `block`

#### `VAL-OIL-001`
- Scope: thermal-oil states
- Rule: thermal-oil bulk temperature must remain within allowed fluid limits
- Action: `block`

#### `VAL-OIL-002`
- Scope: thermal-oil loop
- Rule: modeled line loss must not exceed available loop heat
- Action: `block`

### Group D - ORC screening safeguards

#### `VAL-ORC-001`
- Scope: ORC screening heat-uptake mode
- Rule: screening temperature-gain mode may only be used when the selected property path supports the requested state path
- Action: `block`

#### `VAL-ORC-002`
- Scope: ORC screening heat-uptake mode
- Rule: if the requested working-fluid path crosses an unsupported two-phase region, block temperature-only screening and require duty-based or later detailed mode
- Action: `block`

#### `VAL-ORC-003`
- Scope: ORC screening power estimate
- Rule: gross ORC efficiency must be within the configured physically credible range
- Action: `block` for impossible values, `hard_warning` for aggressive but possible values

#### `VAL-ORC-004`
- Scope: ORC screening power estimate
- Rule: gross electric power must not exceed absorbed ORC heat
- Action: `block`

### Group E - Property and backend integrity

#### `VAL-PROP-001`
- Scope: all property calls
- Rule: selected backend must support the requested fluid and state specification
- Action: `block`

#### `VAL-PROP-002`
- Scope: all property calls
- Rule: extrapolation outside validated correlation range must be surfaced explicitly
- Action: `hard_warning` or `block`, depending on policy

### Group F - Result integrity

#### `VAL-RESULT-001`
- Scope: all major results
- Rule: required result-envelope fields must be present
- Action: `block`

#### `VAL-RESULT-002`
- Scope: all major results
- Rule: reported metrics must carry explicit SI units or explicit dimensionless basis
- Action: `block`

#### `VAL-RESULT-003`
- Scope: all major results
- Rule: `warnings`, `assumptions`, `calc_trace`, and `blocked_state` must always exist
- Action: `block`

## Severity calibration rule

Use `block` when the issue changes physical validity.
Use `hard_warning` when the result may still be useful but has elevated engineering risk.
Use `soft_warning` when the result remains usable with normal caution.

## Minimum tests implied by this rule set

- one positive and one negative test for each blocking rule
- threshold-edge tests for closure and efficiency limits
- unsupported-backend tests
- ORC screening mode rejection tests for unsupported phase paths
