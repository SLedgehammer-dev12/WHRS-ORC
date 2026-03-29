# WHRS ORC Project Instructions

Before planning or coding in this folder, read these files in order:
1. `CONTINUITY.md`
2. `PROJECT_PLAN.md`
3. `SYSTEM_ARCHITECTURE.md`
4. `CALCULATION_BASIS.md`
5. `DOMAIN_MODEL.md`
6. `EQUIPMENT_CONTRACTS.md`
7. `RESULT_SCHEMA.md`
8. `VALIDATION_RULES.md`
9. `TEST_STRATEGY.md`
10. `SESSION_HANDOFF.md`
11. When implementing the first module, also read `EXHAUST_BOILER_CODE_READY_SPEC.md`
12. The relevant project skill:
   - `skills/whrs-orc-architect/SKILL.md` for planning, architecture, documentation, UI/UX, reporting, logging, persistence, and delivery flow
   - `skills/whrs-orc-thermal-calculation-guardian/SKILL.md` for formulas, property strategy, units, solver guards, and engineering validation

Project intent:
- Build a calculation-first engineering application for a natural-gas compressor station waste heat recovery plant.
- Model the process chain:
  - gas turbine exhaust
  - waste heat recovery boiler / thermal-oil heater
  - thermal-oil loop
  - ORC heater train
  - ORC turbine-generator block
  - optional parasitic consumers and net-power accounting
- Support both quick screening and detailed design studies.

Non-negotiable priorities:
- Thermodynamic and heat-transfer correctness before UI polish.
- Internal SI units only.
- Explicit warnings, assumptions, and blocked states for every important calculation.
- No silent property fallback and no hidden efficiency assumptions.
- Every user-facing KPI must be traceable to a clear equation or calculation path.

Core agent roster for this project:
- `Chief Architect`
  - Own system architecture, module boundaries, delivery sequencing, and continuity docs.
- `Thermal Calculation Guardian`
  - Own equations, property choices, unit consistency, physical validation rules, and benchmark cases.
- `Property and Data Librarian`
  - Own fluid databases, thermal-oil correlations, exhaust component data, schema versioning, and source traceability.
- `UI/UX and Reporting Designer`
  - Own operator workflows, flowsheet views, explanation panels, reports, and export formats.
- `Verification and Release Lead`
  - Own test strategy, regression baselines, logging review, release checklists, and update safety.

Working rules:
- Keep engineering core separate from UI state and presentation formatting.
- Keep property lookup logic separate from equipment equations.
- Keep screening ORC power estimation separate from later detailed turbine/pump modeling.
- Keep all results structured:
  - values
  - warnings
  - assumptions
  - calc_trace
  - blocked state, when needed
- Define or update the relevant tests for every meaningful code-generation step.
- Prefer modular equipment contracts over large ad-hoc solver payloads.
- Use `HRS ORC/` and `HRS ORC Version 2/` only as references, not as architecture constraints.

Session continuity rule:
- Update `CONTINUITY.md` whenever architecture direction, priorities, or assumptions change.
- Update `SESSION_HANDOFF.md` at the end of every meaningful work session.
- Update `PROJECT_PLAN.md` when scope, phase ordering, or module strategy changes.
- Update `CALCULATION_BASIS.md` when formulas, KPI definitions, or engineering limits change.
