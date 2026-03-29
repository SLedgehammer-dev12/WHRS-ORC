# Project Plan

## Purpose

Create a trustworthy engineering application for a waste heat recovery ORC plant at a natural-gas compressor station.

The plant boundary is:
- gas turbine exhaust outlet
- waste heat recovery boiler / thermal-oil heater
- thermal-oil circuit
- ORC heat uptake equipment
- ORC turbine-generator
- optional auxiliaries and net-power accounting

## Product pillars

- Calculation correctness first
- Traceability of every KPI
- Fast screening and detailed study in the same product family
- Stable, testable modular architecture
- Operator-friendly UI and explainable outputs

## What the first serious release must do

- Accept realistic exhaust-gas, thermal-oil, and ORC working-fluid inputs.
- Calculate available exhaust heat, recovered heat, ORC absorbed heat, and produced power on a controlled basis.
- Distinguish clearly between:
  - available heat
  - transferred heat
  - gross electric power
  - net electric power
  - component efficiencies
  - overall plant efficiencies
- Explain all warnings, assumptions, and blocked states.
- Generate study-ready reports and persistent case files.

First-release ORC scope decision:
- keep ORC heater train and power block at screening level first
- calculate heat taken from thermal oil
- calculate supported working-fluid temperature gain
- estimate gross electric power and gross efficiencies from absorbed ORC heat
- defer detailed pump and turbine thermodynamics to a later phase

## Core workstreams

### 1. Thermal calculation engine
- Exhaust source characterization
- Waste heat boiler model
- Thermal-oil loop energy balance
- ORC screening heat-uptake block
- ORC screening gross-power block
- Later: turbine, pump, condenser, recuperator, and detailed generator models
- Integrated cycle solver

### 2. Property and data layer
- Exhaust gas component data
- Thermal-oil library and correlations
- Working-fluid property backends
- Equipment template data
- Validation-ready benchmark datasets

### 3. Validation and control mechanisms
- Unit normalization
- Physical input checks
- Energy-closure checks
- Temperature approach and pinch checks
- Oil temperature limit checks
- Solver convergence and bounded-search protections
- Blocked-state handling for non-physical solutions

### 4. UI and UX
- Quick screening workspace
- Detailed flowsheet workspace
- Diagnostics and assumptions panel
- Case comparison views
- Guided data-entry aids and unit conversion helpers
- Goal-driven design selector so the user can choose the governing design target:
  - minimum stack temperature
  - target boiler efficiency
  - target oil outlet temperature
  - target transferred power
  - exchanger effectiveness or UA
  - minimum pinch approach

### 5. Reporting
- Engineering summary report
- Detailed calculation appendix
- Warnings and assumptions section
- Version and source traceability section
- Export to markdown, PDF, and tabular data where practical

### 6. Logging and observability
- Application log
- Solver trace log
- Validation log
- Error log
- Optional user action/session audit for report reproducibility

### 7. Persistence and updates
- Saved case storage
- Database schema/version migration
- Fluid library updates
- Release notes and compatibility checks

## Architecture phases

### Phase 0 - Planning and baseline
- Create planning documents and project skills.
- Define architecture, priorities, and continuity workflow.
- Identify reusable references from prior projects.

### Phase 1 - Engineering basis and data strategy
- Freeze KPI names and efficiency definitions.
- Freeze control-volume boundaries.
- Decide first property backend strategy.
- Define the first data catalog structure.

### Phase 2 - Domain contracts
- Define streams, state points, fluids, compositions, and result contracts.
- Define equipment request/response objects.
- Define standard warning and blocked-state schema.

### Phase 3 - Thermal backbone
- Implement exhaust source and waste heat boiler.
- Implement thermal-oil linking.
- Implement ORC screening heat uptake and absorbed-heat accounting.

### Phase 4 - ORC power block
- Implement screening gross-power estimation from absorbed heat.
- Later extend to turbine, pump, generator, condenser placeholder, and optional recuperator.
- Separate gross-power and net-power reporting as detail grows.

### Phase 5 - System orchestration
- Link equipment modules through an orchestration layer.
- Add scenario, sensitivity, and comparison workflows.

### Phase 6 - UI shell
- Build quick screening first.
- Add detailed flowsheet workspace after solver contracts stabilize.
- Keep UI thin over the model layer.

### Phase 7 - Reporting, logging, and persistence
- Build case save/load flow.
- Build engineering report generation.
- Build structured logging and release metadata.

### Phase 8 - Verification and release hardening
- Build regression benchmarks.
- Add validation against known cases or literature references.
- Run release checklist for units, warnings, reports, and crash handling.

## Recommended folder direction

```text
WHRS ORC/
  AGENTS.md
  CONTINUITY.md
  PROJECT_PLAN.md
  SYSTEM_ARCHITECTURE.md
  CALCULATION_BASIS.md
  DOMAIN_MODEL.md
  EQUIPMENT_CONTRACTS.md
  RESULT_SCHEMA.md
  VALIDATION_RULES.md
  TEST_STRATEGY.md
  EXHAUST_BOILER_CODE_READY_SPEC.md
  SESSION_HANDOFF.md
  ToDo.md
  skills/
    whrs-orc-architect/
    whrs-orc-thermal-calculation-guardian/
  src/
    whrs_orc/
      domain/
      properties/
      equipment/
      solvers/
      ui/
      reporting/
      logging/
      persistence/
  data/
    fluids/
    equipment/
    cases/
  tests/
```

## Immediate planning deliverables

- Data strategy for fluids and templates
- UI/UX concept for quick screening
- Logging and reporting contract draft
- Property-backend decision matrix
- Benchmark-case pack for the first thermal modules
- First implementation pass for `exhaust source + waste heat boiler`

## Do not do early

- Do not start with cosmetic UI work.
- Do not hardcode overall ORC efficiency without exposing its basis.
- Do not mix engineering solvers and widget state.
- Do not add economics before thermal and power balances are trusted.
