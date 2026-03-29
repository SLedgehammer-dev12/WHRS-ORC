---
name: whrs-orc-thermal-calculation-guardian
description: Define, review, or validate WHRS ORC thermal and thermodynamic calculations for exhaust gas, thermal oil, and ORC power production. Use when selecting property backends, writing equations, setting unit rules, defining pinch and closure checks, creating blocked-state logic, or preparing engineering test cases inside `WHRS ORC/`.
---

# WHRS ORC Thermal Calculation Guardian

Read these files before changing formulas or solver rules:
1. `CALCULATION_BASIS.md`
2. `SYSTEM_ARCHITECTURE.md`
3. `PROJECT_PLAN.md`
4. `CONTINUITY.md`

Use this skill to protect physical correctness and explainability before solver code expands.

## Workflow

1. Identify the control volume and the exact inputs and outputs.
2. Define the property path for each fluid before writing equations.
3. Solve with explicit units and explicit assumptions.
4. Add validation rules before trusting the result.
5. Return enough trace data to explain the result or the blocked state.

## Mandatory engineering guardrails

- Keep internal units in SI.
- Never mix property lookup code and user-interface formatting.
- Never present a non-physical result as valid.
- Never hide which backend or correlation produced a property.
- Always distinguish heat basis and efficiency basis.
- Always include warnings, assumptions, and calc_trace in major results.

## Minimum validation topics

- composition sums
- positive flow rates
- monotonic heating and cooling directions
- stack temperature floor
- oil temperature limits
- pinch or approach temperature limits
- energy-closure tolerance
- backend and phase compatibility
- impossible duty rejection

## Preferred property direction

- exhaust gas mixtures: prefer a validated mixture-capable backend
- ORC working fluid states: prefer a backend with reliable phase-aware pure-fluid properties
- supporting engineering correlations: use dedicated engineering libraries where they are stronger than the main property backend

## Deliverables this skill should push toward

- stable equations
- explicit KPI definitions
- validation and blocked-state rules
- benchmark-ready test cases
- explainable solver outputs
