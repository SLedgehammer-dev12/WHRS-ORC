# Equipment Contracts

## Purpose

This document defines the first equipment interface contracts for WHRS ORC.

The intent is to make each physical block:
- independently testable
- solver-friendly
- report-friendly
- reusable in both quick and detailed workflows

## Standard equipment contract pattern

Every equipment block should follow the same high-level pattern.

### Common request shell

Required fields:
- `equipment_id`
- `mode`
- `input_streams`
- `constraints`

Recommended fields:
- `parameters`
- `options`
- `requested_outputs`
- `case_context`

### Common result shell

Required fields:
- `equipment_id`
- `mode`
- `solved_streams`
- `values`
- `warnings`
- `assumptions`
- `calc_trace`
- `blocked_state`

Recommended fields:
- `metadata`
- `energy_residual_w`
- `mass_residual_kg_s`
- `solver_stats`

## Common blocked-state triggers

Any equipment block may block when:
- a required stream is missing
- a property backend cannot resolve the requested state
- flow rates are non-positive
- temperatures or pressures are non-physical
- a requested duty exceeds physically available upstream energy
- a required pinch or approach temperature becomes non-positive
- a fluid limit is exceeded

## Module 01 - Exhaust Source Contract

### Purpose

Represent the gas-turbine exhaust as a formal equipment source rather than an unstructured input bundle.

### First supported modes

- `available_heat_from_stack_limit`
- `released_heat_from_outlet_temperature`
- `screening_from_validated_cp`

### Request object direction

Required inputs:
- `exhaust_inlet_stream`
- `constraints`

Expected stream meaning:
- `exhaust_inlet_stream.inlet.temp_k` = turbine exhaust temperature
- `exhaust_inlet_stream.mass_flow_kg_s` = total exhaust mass flow
- `exhaust_inlet_stream.fluid.composition` = exhaust composition

Required constraints by mode:
- `available_heat_from_stack_limit`
  - `stack_min_temp_k`
- `released_heat_from_outlet_temperature`
  - resolved outlet temperature

### Result contract

Required outputs:
- `available_heat_w` or `released_heat_w`
- `cp_mix_avg_j_kg_k`
- `resolved_exhaust_outlet_stream`

Recommended outputs:
- `composition_basis_used`
- `property_backend_used`

## Module 02 - Waste Heat Boiler Contract

### Purpose

Calculate heat transfer from exhaust gas into the thermal-oil circuit.

### First supported modes

- `performance`
- `design`

### Design-mode selector

When `mode = design`, the user must choose one governing design driver.

First supported design drivers:
- `minimum_stack_temperature`
- `target_boiler_efficiency`
- `target_oil_outlet_temperature`
- `target_transferred_power`
- `target_effectiveness`
- `target_ua`
- `minimum_pinch_approach`

### Request object direction

Required inputs:
- `exhaust_hot_stream`
- `oil_cold_stream`
- `constraints`

Recommended parameters:
- `heat_loss_fraction`
- `fouling_factor`
- `pressure_drop_model`

Expected stream meanings:
- `exhaust_hot_stream.inlet.temp_k` = boiler hot-side inlet temperature
- `exhaust_hot_stream.outlet.temp_k` = boiler hot-side outlet temperature when known
- `oil_cold_stream.inlet.temp_k` = oil inlet temperature
- `oil_cold_stream.outlet.temp_k` = oil outlet temperature when known

Required constraints:
- `stack_min_temp_k`
- `min_pinch_delta_t_k`
- `max_closure_fraction`
- oil maximum bulk temperature from fluid limits

Required when `mode = design`:
- `design_driver`
- the matching target value for the selected design driver

### Result contract

Required outputs:
- `q_exhaust_available_w`
- `q_boiler_transferred_w`
- `q_oil_absorbed_w`
- `eta_boiler`
- `resolved_exhaust_stream`
- `resolved_oil_stream`

Recommended outputs:
- `closure_error_w`
- `closure_ratio`
- `min_delta_t_k`
- `stack_margin_k`
- `heat_loss_w`
- `design_driver_used`
- `design_target_value`
- `resolved_design_basis`

### Boiler-specific block rules

Block or hard-warn when:
- `q_oil_absorbed_w > q_exhaust_available_w`
- oil outlet temperature exceeds fluid limits
- resolved stack temperature is below the allowed minimum
- minimum approach temperature is non-positive
- design mode is requested without a governing design driver
- the chosen design driver cannot produce a unique physical solution with the provided inputs

## Module 03 - Thermal Oil Loop Contract

### Purpose

Represent the transport of energy from the boiler outlet to the ORC heater train.

### First supported modes

- `adiabatic_link`
- `rated_heat_loss`
- `target_delivery_temperature`

### Request object direction

Required inputs:
- `oil_supply_stream`
- `oil_return_stream`
- `constraints`

Recommended parameters:
- `line_heat_loss_w`
- `line_heat_loss_fraction`
- `line_pressure_drop_pa`
- `pump_efficiency`

### Result contract

Required outputs:
- `oil_delivered_stream`
- `oil_return_resolved_stream`
- `q_loop_loss_w`

Recommended outputs:
- `delta_t_loop_k`
- `estimated_pump_power_w`
- `line_pressure_drop_pa`

### Thermal-oil-loop block rules

Block or hard-warn when:
- delivered oil temperature becomes lower than the required ORC-side inlet basis
- modeled loop losses exceed available oil heat
- return temperature becomes non-physical

## Module 04 - ORC Screening Heat Uptake Contract

### Purpose

Calculate heat transfer from thermal oil into the ORC working fluid without entering full cycle detail.

### First supported modes

- `screening_from_oil_side`
- `single_phase_temperature_gain`
- `known_orc_heat_input`

### Request object direction

Required inputs:
- `oil_hot_stream`
- `wf_cold_stream`
- `constraints`

Recommended parameters:
- `wf_cp_method`
- `screening_phase_policy`
- `target_wf_outlet_temp_k`

Expected stream meanings:
- `oil_hot_stream.inlet.temp_k` = ORC heater train oil inlet temperature
- `wf_cold_stream.inlet` = ORC working-fluid inlet state to the screening heater block

### Result contract

Required outputs:
- `q_orc_absorbed_w`
- `wf_temp_gain_k`
- `resolved_oil_stream`
- `resolved_wf_stream`

Recommended outputs:
- `min_approach_k`
- `wf_final_heater_outlet_state`
- `phase_path_supported`

### ORC-screening-heat block rules

Block or hard-warn when:
- requested heat input cannot achieve the requested outlet state
- minimum approach becomes non-positive
- the property backend cannot support the requested phase path
- temperature-only screening is asked to cross an unsupported two-phase region

## Module 05 - ORC Screening Gross Power Contract

### Purpose

Estimate gross electric power from absorbed ORC heat on a screening basis.

### First supported modes

- `gross_power_from_efficiency`
- `gross_efficiency_from_power`

### Required inputs

- `q_orc_absorbed_w`
- either:
  - `eta_orc_gross_target`
  - or `gross_electric_power_target_w`

### Result contract

Required outputs:
- `gross_electric_power_w`
- `eta_orc_gross`

Recommended outputs:
- `eta_system_gross`
- `screening_basis_note`

### ORC-screening-power block rules

Block or hard-warn when:
- `gross_electric_power_w > q_orc_absorbed_w`
- efficiency is outside configured credible limits
- absorbed ORC heat is non-positive

## Module 06 - Future Detailed Power-Block Contracts

### Purpose

Reserve the later transition to detailed pump and turbine-generator models.

Deferred detailed modules:
- pump
- turbine
- generator
- condenser
- recuperator, when needed

## Module 07 - Plant System Contract

### Purpose

Aggregate equipment modules into a single plant solve.

### First supported modes

- `quick_screening`
- `integrated_detailed_cycle`

### Request object direction

Required fields:
- selected equipment payloads
- global constraints
- case metadata

### Result contract

Required outputs:
- `plant_kpis`
- `stream_table`
- `equipment_results`
- `warnings`
- `assumptions`
- `calc_trace`
- `blocked_state`

Recommended outputs:
- `gross_vs_net_power_breakdown`
- `energy_balance_summary`
- `report_payload`

## Metadata contract

Every equipment result must return:
- `warnings`
- `assumptions`
- `calc_trace`
- `blocked_state`

This is mandatory even in early screening mode.

## First code mapping

The initial Python implementation should eventually be split into:
- `src/whrs_orc/equipment/contracts.py`
- `src/whrs_orc/equipment/exhaust_source.py`
- `src/whrs_orc/equipment/waste_heat_boiler.py`
- `src/whrs_orc/equipment/thermal_oil_loop.py`
- `src/whrs_orc/equipment/orc_screening_heat_uptake.py`
- `src/whrs_orc/equipment/orc_screening_power.py`

Deferred detailed files later:
- `src/whrs_orc/equipment/pump.py`
- `src/whrs_orc/equipment/turbine_generator.py`
