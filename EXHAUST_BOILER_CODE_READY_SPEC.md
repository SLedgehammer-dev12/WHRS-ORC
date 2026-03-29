# Exhaust Source + Waste Heat Boiler Code-Ready Spec

## Purpose

This document translates the planning baseline into the first implementation-ready module specification.

Initial implementation scope:
- exhaust available-heat calculation
- exhaust released-heat calculation
- waste heat transfer from exhaust to thermal oil
- boiler efficiency and closure reporting

Out of scope for this module:
- detailed ORC thermodynamic cycle
- detailed turbine and pump modeling
- economic calculations

## Implementation objective

Deliver the first trustworthy thermal backbone block with:
- explicit request and result contracts
- structured warnings and blocked states
- deterministic unit tests

## First file plan

Recommended first implementation files:
- `src/whrs_orc/domain/models.py`
- `src/whrs_orc/domain/result_schema.py`
- `src/whrs_orc/solvers/validation_rules.py`
- `src/whrs_orc/properties/exhaust_properties.py`
- `src/whrs_orc/properties/thermal_oil_properties.py`
- `src/whrs_orc/equipment/exhaust_source.py`
- `src/whrs_orc/equipment/waste_heat_boiler.py`

Recommended first test files:
- `tests/test_result_schema.py`
- `tests/test_validation_rules.py`
- `tests/test_exhaust_source.py`
- `tests/test_waste_heat_boiler.py`

## Required coding contracts

### Domain layer

Implement at least:
- `ComponentFraction`
- `CompositionSpec`
- `PropertyModelSpec`
- `FluidLimitSpec`
- `FluidSpec`
- `StatePoint`
- `ProcessStream`

### Result layer

Implement at least:
- `MetricValue`
- `WarningRecord`
- `AssumptionRecord`
- `CalcTraceEntry`
- `BlockedState`
- `ResultEnvelope`

### Validation layer

Implement first rules for:
- composition sum
- positive flow
- temperature ordering
- stack floor
- oil max temperature
- available-heat exceedance
- result-envelope completeness

## Property abstraction strategy

Do not hardwire the first solver directly to a third-party library.

Create minimal property-provider interfaces:
- `ExhaustPropertyProvider`
- `ThermalOilPropertyProvider`

Required provider capabilities:
- average or integrated `cp`
- supported-temperature-range visibility
- backend identification for traceability

This keeps the first module implementable before the final backend matrix is frozen.

## Exhaust source solver requirements

### Supported modes

- `available_heat_from_stack_limit`
- `released_heat_from_outlet_temperature`

### Required inputs

- exhaust composition
- exhaust mass flow
- exhaust inlet temperature
- either:
  - minimum stack temperature
  - or resolved outlet temperature

### Required outputs

- available or released heat in `W`
- average or integrated `cp`
- resolved exhaust outlet state
- warnings
- assumptions
- calc trace
- blocked state

## Waste heat boiler solver requirements

### Supported modes

- `performance`
- `design`

### Design drivers for first implementation pass

The first boiler design implementation should support these selectable drivers:
- `minimum_stack_temperature`
- `target_boiler_efficiency`
- `target_oil_outlet_temperature`

The following drivers should be planned in the interface and validation contract, but may be implemented in a later pass if needed:
- `target_transferred_power`
- `target_effectiveness`
- `target_ua`
- `minimum_pinch_approach`

### Required inputs

- hot-side exhaust stream
- cold-side thermal-oil stream
- stack minimum temperature
- closure tolerance
- oil temperature limits

### Required outputs

- `q_exhaust_available_w`
- `q_boiler_transferred_w`
- `q_oil_absorbed_w`
- `eta_boiler`
- `closure_error_w`
- `closure_ratio`
- resolved hot-side and cold-side streams
- warnings
- assumptions
- calc trace
- blocked state

Required design-mode metadata:
- `design_driver_used`
- `design_target_value`
- `resolved_design_basis`

## Suggested solver function split

- `validate_exhaust_source_request(...)`
- `solve_exhaust_available_heat(...)`
- `solve_exhaust_released_heat(...)`
- `validate_boiler_request(...)`
- `validate_boiler_design_driver(...)`
- `solve_boiler_performance(...)`
- `solve_boiler_design(...)`

## Acceptance criteria

The first implementation is acceptable when:
- all outputs use SI internally
- blocked cases return structured results, not crashes
- energy basis is traceable in the result envelope
- boiler efficiency basis is explicit
- stack-floor violations are blocked
- oil-limit violations are blocked
- result schema tests pass
- validation tests pass
- exhaust and boiler regression tests pass

## Minimum test list

### Result schema tests
- valid result-envelope construction
- blocked result-envelope construction
- missing mandatory field rejection

### Validation tests
- composition sum pass/fail
- negative flow fail
- hot/cold temperature ordering fail
- stack-floor fail
- oil limit fail

### Exhaust source tests
- constant-`cp` available-heat case
- constant-`cp` released-heat case
- stack-limit block case

### Waste heat boiler tests
- direct-performance heat balance case
- design mode with target boiler efficiency case
- design mode with target oil outlet temperature case
- design mode with minimum stack temperature case
- closure-ratio warning case
- design mode missing-driver block case
- design mode missing-target-value block case
- impossible duty block case

## First implementation note

Keep this module independent from UI code.
The UI should consume its result envelope only after solver behavior is trusted.
