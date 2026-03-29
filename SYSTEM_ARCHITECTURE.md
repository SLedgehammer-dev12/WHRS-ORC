# System Architecture

## Design bias

The product must be calculation-first and explanation-first.
The UI exists to drive and understand the engineering model, not to hide it.

## Layered architecture

### Layer 1 - Domain and contracts

Purpose:
- Define shared engineering objects and stable interfaces.

Main contents:
- fluid identity
- composition
- state point
- process stream
- equipment request and result contracts
- warning, assumption, and calc-trace contracts

### Layer 2 - Properties and fluid data

Purpose:
- Resolve thermophysical data without contaminating equipment logic.

Main contents:
- property backend adapters
- fluid catalog
- thermal-oil correlations
- exhaust-gas component data
- working-fluid configuration
- unit normalization helpers

Candidate libraries:
- `CoolProp`
- `Cantera`
- `thermo`
- `chemicals`
- `ht`
- `numpy`
- `scipy`
- `pydantic`
- `pint`
- `pandas`

### Layer 3 - Equipment models

Purpose:
- Keep each physical block independently testable.

Planned equipment blocks:
- exhaust source
- waste heat recovery boiler
- thermal-oil loop
- ORC screening heat-uptake block
- ORC screening gross-power block
- later detailed ORC preheater
- later detailed ORC evaporator
- later detailed ORC superheater
- recuperator
- turbine
- pump
- condenser
- generator / electrical output block

### Layer 4 - Solver orchestration

Purpose:
- Coordinate execution order, convergence, and cross-equipment consistency.

Responsibilities:
- stream linking
- scenario setup
- sequence control
- convergence handling
- blocked-state propagation
- integrated KPI assembly

### Layer 5 - Reporting, logging, and persistence

Purpose:
- Make the application auditable and usable in real engineering workflows.

Subsystems:
- report builder
- structured result serializer
- application and solver logging
- saved cases
- version and migration management

### Layer 6 - UI adapters

Purpose:
- Present engineering data cleanly without owning the engineering logic.

Views to plan:
- quick screening workspace
- detailed flowsheet workspace
- diagnostics workspace
- scenario comparison workspace
- report preview/export workspace

## UI and UX direction

### UX principles

- Keep the first screen useful within minutes.
- Expose important assumptions before the user trusts a result.
- Keep units user-friendly while preserving SI internally.
- Surface engineering diagnostics close to the flowsheet.
- Show what is known, assumed, solved, and blocked.

### Recommended interaction model

- `Quick Screening`
  - fast entry for exhaust, oil, and power basis
  - simplified ORC heat-to-power estimation
  - high-level KPIs
  - major warnings and feasibility indicators
- `Detailed Study`
  - explicit equipment and state-point views
  - stage-level ORC heat-transfer visibility
  - turbine/pump/generator breakdown
- `Diagnostics`
  - energy balance table
  - temperature approach table
  - property backend and source notes
  - solver trace summary

### Design-mode interaction rule

When the user selects design mode for an equipment block, the UI should ask which engineering target drives the solve.

For the first waste heat boiler release, supported design drivers should be:
- minimum stack temperature
- target boiler efficiency
- target oil outlet temperature
- target transferred power
- exchanger effectiveness or UA
- minimum pinch approach

The selected design driver must be visible in:
- the input summary
- the result metadata
- the exported report

## Reporting architecture

Every report should be composed from structured results, not copied from UI widgets.

Minimum report sections:
- project and case metadata
- input summary
- model assumptions
- calculation results
- KPI definitions
- warnings and blocked states
- calculation trace appendix
- software version and data-source version

## Logging architecture

Keep logs separate by purpose:
- `application.log`
  - startup, shutdown, file IO, report export, settings
- `solver.log`
  - solve path, iteration notes, convergence, blocked states
- `validation.log`
  - input issues, unit issues, physical rule violations
- `errors.log`
  - uncaught exceptions and crash diagnostics

Recommended logging features:
- case identifier
- session timestamp
- module name
- severity
- calculation mode
- solver duration

## Data and persistence strategy

Use a hybrid approach:
- JSON or YAML seed catalogs for fluids, equipment templates, and defaults
- SQLite for saved studies, report metadata, and versioned local records

Persist at least:
- case inputs
- selected fluid sources
- chosen calculation mode
- result summary
- warnings and assumptions
- app version and data version

## Update strategy

Plan updates from the beginning:
- keep an app version manifest
- keep a data version manifest
- add schema migrations for saved cases
- keep release notes
- detect incompatible saved-case versions

## Reference rule

Use prior `HRS ORC` projects for useful formulas, data seeds, and lessons learned.
Do not let their file structure or UI coupling define this architecture.
