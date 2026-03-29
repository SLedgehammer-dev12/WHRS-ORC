---
name: whrs-orc-architect
description: Plan, structure, or refactor the WHRS ORC engineering application for gas-turbine exhaust heat recovery to thermal oil and ORC power generation. Use when defining project phases, module boundaries, folder layout, documentation flow, agent roles, UI/UX direction, reporting, logging, persistence, or update strategy inside `WHRS ORC/`.
---

# WHRS ORC Architect

Read these files before changing project structure or planning direction:
1. `CONTINUITY.md`
2. `PROJECT_PLAN.md`
3. `SYSTEM_ARCHITECTURE.md`
4. `CALCULATION_BASIS.md`
5. `AGENTS.md`

Use this skill to keep WHRS ORC calculation-first and coherent while the product grows.

## Workflow

1. Clarify which layer is changing:
   - architecture and folder structure
   - documentation and continuity
   - UI/UX direction
   - reporting, logging, persistence
   - delivery sequencing
2. Keep the engineering model ahead of the presentation layer.
3. Keep equipment boundaries, result contracts, and continuity docs explicit.
4. Reuse earlier `HRS ORC` projects only as references for requirements, formulas, and lessons learned.
5. Update continuity documents when architecture or priorities change.

## Architecture guardrails

- Keep internal units in SI.
- Keep property lookup, equipment equations, solver orchestration, and UI separate.
- Keep warnings, assumptions, and calc traces visible in the result contract.
- Keep quick screening and detailed study as separate user experiences over the same model backbone.
- Keep project docs current enough that a later session can restart without hidden context.

## Update rules

- Update `CONTINUITY.md` when architecture direction, assumptions, or priorities change.
- Update `PROJECT_PLAN.md` when scope, phase ordering, or module strategy changes.
- Update `SESSION_HANDOFF.md` at the end of meaningful work.
- Update `CALCULATION_BASIS.md` if KPI definitions or engineering basis change.

## Avoid

- Building UI-first without a stable engineering contract.
- Mixing widget state with solver state.
- Hiding fallback assumptions inside presentation logic.
- Copying Version 1 folder structure without a clear reason.
