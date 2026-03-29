# Result Schema

## Purpose

This document defines the common result envelope for WHRS ORC.

The same schema must support:
- quick screening calculations
- detailed equipment solves
- reporting
- logging
- regression testing

## Design principles

- Always return a structured result, even when blocked.
- Keep values machine-readable first and presentation-ready second.
- Keep units explicit.
- Keep warnings, assumptions, and calc trace mandatory.
- Never encode physical meaning only in free text.

## Top-level result envelope

Every major calculation should return a result object with these required fields:

- `result_id`
- `model_name`
- `model_version`
- `status`
- `values`
- `warnings`
- `assumptions`
- `calc_trace`
- `blocked_state`
- `metadata`

Recommended fields:
- `solved_streams`
- `tables`
- `artifacts`
- `input_echo`

## Status values

Supported `status` values:
- `success`
- `warning`
- `blocked`
- `error`

Rules:
- `blocked_state.blocked = true` implies `status = blocked`
- unhandled exceptions should be converted to controlled `error` results only at a safe application boundary
- equipment solvers should prefer `blocked` over uncaught failure when the issue is physical or expected

## `values` contract

`values` should be a dictionary keyed by stable metric IDs.

Each metric value should use this minimum structure:
- `key`
- `display_name`
- `value_si`
- `unit_si`

Recommended fields:
- `display_unit`
- `display_value`
- `basis`
- `source`
- `lower_bound_si`
- `upper_bound_si`
- `notes`

Example metric keys:
- `q_exhaust_available_w`
- `q_oil_absorbed_w`
- `q_orc_absorbed_w`
- `p_gross_electric_w`
- `eta_boiler`
- `eta_orc_gross`
- `eta_system_gross`

## `solved_streams` contract

`solved_streams` should contain stream snapshots relevant to the calculation.

Each stream snapshot should contain at least:
- `stream_id`
- `fluid_id`
- `mass_flow_kg_s`
- `inlet`

Recommended fields:
- `outlet`
- `display_name`
- `property_model`

Each state snapshot should contain any solved or echoed SI properties that are relevant:
- `temp_k`
- `pressure_pa`
- `enthalpy_j_kg`
- `quality_mass`
- `phase_hint`

## `warnings` contract

Each warning record should contain:
- `code`
- `message`
- `severity`

Recommended fields:
- `source`
- `affected_object`
- `recommended_action`

Severity values:
- `info`
- `soft_warning`
- `hard_warning`

## `assumptions` contract

Each assumption record should contain:
- `code`
- `message`

Recommended fields:
- `source`
- `impact_level`
- `applied_value`

## `calc_trace` contract

`calc_trace` is mandatory for all major equipment results.

Each trace entry should contain:
- `step`
- `message`

Recommended fields:
- `equation_ref`
- `value_snapshot`
- `backend_used`
- `duration_ms`

Trace entries should be concise and structured enough for debugging and reporting.

## `blocked_state` contract

Every result must include a `blocked_state` object.

Required fields:
- `blocked`

Required when blocked:
- `code`
- `reason`

Recommended fields:
- `source`
- `suggested_action`

Examples:
- unsupported property path
- stack temperature below limit
- non-physical heat duty
- exceeded thermal-oil temperature limit

## `metadata` contract

`metadata` should contain run context and traceability information.

Recommended fields:
- `calculation_mode`
- `design_driver`
- `case_id`
- `run_timestamp`
- `execution_time_ms`
- `property_backends`
- `data_versions`
- `tolerance_set`

## Serialization rules

- Do not return `NaN`, `inf`, or unitless ambiguous numeric values.
- Keep SI storage values separate from optional display formatting.
- Use stable snake_case keys for machine parsing.
- Preserve unknown optional fields during save/load when practical.

## Reporting rule

Reports and UI should be generated from this schema, not from raw internal solver variables.

## Minimum tests implied by this schema

- required-field presence test
- blocked result shape test
- warning and assumption list shape test
- metric-unit consistency test
- serialization round-trip test
