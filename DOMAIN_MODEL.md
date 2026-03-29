# Domain Model

## Purpose

This document defines the shared engineering objects for WHRS ORC before solver code is written.

The goal is to prevent the project from collapsing into:
- ad-hoc form fields
- hidden unit conversions
- equipment-specific variable packs
- result objects that cannot be compared across modules

## Core modeling principles

- Represent physical meaning first, UI widgets second.
- Keep internal units in SI.
- Separate:
  - fluid identity
  - composition
  - property model
  - thermodynamic state
  - stream flow data
  - equipment request/response contracts
- Make every major result traceable and auditable.

## Core domain objects

### 1. `ComponentFraction`

Represents one component inside a mixture definition.

Required fields:
- `component_id`
- `fraction`

Optional fields:
- `display_name`
- `source_reference`

### 2. `CompositionSpec`

Represents the composition basis for a mixture.

Required fields:
- `basis`
- `components`

Recommended fields:
- `reference_state`
- `normalized`

First supported basis values:
- `mole_fraction`
- `mass_fraction`

Optional future basis values:
- `dry_mole_fraction`
- `wet_mole_fraction`

For gas-turbine exhaust, the preferred normalized internal basis should be mole fraction.

### 3. `PropertyModelSpec`

Represents how properties are resolved for a fluid.

Required fields:
- `backend_id`
- `model_id`

Recommended fields:
- `data_source`
- `data_version`
- `correlation_id`
- `allow_extrapolation`
- `notes`

Examples:
- exhaust mixture through `Cantera`
- thermal-oil correlation from vendor or internal JSON catalog
- ORC pure-fluid state through `CoolProp`

### 4. `FluidLimitSpec`

Represents engineering operating limits associated with a fluid.

Optional fields:
- `min_bulk_temp_k`
- `max_bulk_temp_k`
- `max_film_temp_k`
- `min_pressure_pa`
- `max_pressure_pa`
- `notes`

This object is especially important for:
- thermal oils
- ORC working fluids near phase limits

### 5. `FluidSpec`

Represents fluid identity and its property-resolution path.

Required fields:
- `fluid_id`
- `display_name`
- `kind`
- `property_model`

Optional fields:
- `composition`
- `limits`
- `source_reference`
- `allow_manual_entry`
- `metadata`

First supported fluid kinds:
- `exhaust_gas`
- `thermal_oil`
- `working_fluid`
- `cooling_medium`
- `utility`

### 6. `StatePoint`

Represents one thermodynamic location in the flowsheet.

Required fields:
- `tag`

Optional but expected fields:
- `temp_k`
- `pressure_pa`
- `enthalpy_j_kg`
- `entropy_j_kg_k`
- `quality_mass`
- `density_kg_m3`
- `cp_j_kg_k`
- `phase_hint`

Rules:
- A state point may start partially specified and be completed by a solver.
- UI inputs in `degC`, `bar`, or `kPa` must be normalized before becoming a `StatePoint`.
- `quality_mass` is only meaningful when the selected property model supports two-phase interpretation.

### 7. `ProcessStream`

Represents a physical stream that connects equipment blocks.

Required fields:
- `stream_id`
- `display_name`
- `fluid`
- `mass_flow_kg_s`
- `inlet`

Optional fields:
- `outlet`
- `source_equipment_id`
- `target_equipment_id`
- `metadata`

This object should be used for:
- exhaust gas
- thermal oil
- ORC working fluid
- cooling utility streams

### 8. `ConstraintSpec`

Represents common physical and numerical constraints used across solvers.

Recommended fields:
- `stack_min_temp_k`
- `min_pinch_delta_t_k`
- `min_approach_delta_t_k`
- `max_closure_fraction`
- `max_iterations`
- `solver_tolerance`
- `allow_soft_warnings`

This object avoids spreading hidden solver rules across the codebase.

### 9. `WarningRecord`

Represents a surfaced caution that does not necessarily block a result.

Required fields:
- `code`
- `message`

Recommended fields:
- `severity`
- `source`
- `affected_object`

### 10. `AssumptionRecord`

Represents an explicit assumption applied during a calculation.

Required fields:
- `code`
- `message`

Recommended fields:
- `source`
- `impact_level`

### 11. `CalcTraceEntry`

Represents a traceable calculation step or solver event.

Required fields:
- `step`
- `message`

Recommended fields:
- `equation_ref`
- `value_snapshot`
- `backend_used`

### 12. `BlockedState`

Represents a non-physical or unsupported result state.

Required fields:
- `blocked`

Recommended fields when blocked:
- `code`
- `reason`
- `source`
- `suggested_action`

### 13. `ResultEnvelope`

Represents the minimum common result shell for all major calculations.

Required fields:
- `values`
- `warnings`
- `assumptions`
- `calc_trace`
- `blocked_state`

Recommended fields:
- `metadata`
- `units_basis`
- `version_info`

### 14. `CaseDefinition`

Represents one saved engineering study case.

Required fields:
- `case_id`
- `case_name`
- `calculation_mode`
- `input_payload`

Recommended fields:
- `created_at`
- `updated_at`
- `app_version`
- `data_version`
- `notes`

## State-variable philosophy

The state model must support both screening and detailed thermodynamic work.

That means:
- screening mode may use only temperature, pressure, and flow
- detailed mode may require enthalpy, entropy, vapor quality, and phase-aware logic
- the same `StatePoint` object should survive both levels without redesign

## First-release stream identity set

These stream identifiers should remain stable across documents and code.

### Exhaust side
- `exhaust_turbine_out`
- `exhaust_boiler_in`
- `exhaust_boiler_out`
- `stack_out`

### Thermal-oil side
- `oil_loop_return`
- `oil_boiler_in`
- `oil_boiler_out`
- `oil_orc_supply`
- `oil_orc_return`

### ORC working-fluid side
- `wf_pump_out`
- `wf_preheater_out`
- `wf_evaporator_out`
- `wf_superheater_out`
- `wf_turbine_out`
- `wf_condenser_out`

### Cooling and auxiliaries
- `cooling_in`
- `cooling_out`

## Naming and units rules

- Temperatures in the model layer must be stored as `K`.
- Pressures in the model layer must be stored as `Pa`.
- Enthalpy must be stored as `J/kg`.
- Entropy must be stored as `J/kg/K`.
- Heat duty and power must be stored as `W`.
- Mass flow must be stored as `kg/s`.
- UI labels may use localized engineering units, but conversion belongs outside the domain layer.

## Why this model matters

This model gives the project:
- stable equipment boundaries
- reusable solver inputs
- reportable state-point tables
- easier regression testing
- fewer hidden assumptions between quick and detailed workflows

## First code mapping

The initial Python implementation should eventually be split into:
- `src/whrs_orc/domain/models.py`
- `src/whrs_orc/domain/result_contracts.py`
- `src/whrs_orc/domain/case_models.py`
