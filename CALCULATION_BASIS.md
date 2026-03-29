# Calculation Basis

## Purpose

This document defines the engineering calculation philosophy for WHRS ORC before solver code is written.

The first priority is to produce physically correct, explainable, and testable calculations for:
- waste heat availability in gas turbine exhaust
- heat transfer into thermal oil
- heat transfer from thermal oil into the ORC working fluid
- gross and later net electric power production

## Core engineering principles

- Use explicit control volumes.
- Keep all internal units in SI.
- Separate property lookup from balance equations.
- Prefer transparent energy balances over opaque fitted shortcuts.
- Block non-physical solutions instead of hiding them.
- Return:
  - values
  - warnings
  - assumptions
  - calc_trace
  - blocked state, when required

## Plant calculation boundary

The long-term plant boundary is:
- exhaust gas from the turbine outlet
- waste heat recovery boiler / thermal-oil heater
- thermal-oil circulation path
- ORC preheater / evaporator / superheater
- ORC turbine-generator
- pump and optional recuperator
- condenser and later parasitic consumers

## Release strategy

### Release track A - quick screening

Use this track first to support rapid engineering checks.

Target outputs:
- available exhaust heat
- recovered heat to thermal oil
- heat delivered to ORC
- supported ORC working-fluid temperature gain
- gross electric power, either:
  - user-entered for back-calculated efficiency, or
  - estimated from screening gross-efficiency basis
- boiler efficiency
- ORC gross efficiency
- overall gross system efficiency

### Release track B - detailed thermodynamic model

Use this track after the thermal backbone is trusted.

Target outputs:
- state-point table
- stage-wise ORC heat-transfer duties
- turbine and pump thermodynamic states
- gross and net power breakdown
- full warning and assumption trace

## Two user workflows

The product should support two distinct workflows:

### 1. Existing plant performance workflow

Use when the user has measured or known operating data.

Typical waste heat boiler inputs:
- exhaust composition
- exhaust inlet temperature
- exhaust outlet temperature
- exhaust mass flow
- selected thermal oil
- oil inlet temperature
- oil outlet temperature
- oil mass flow

Primary outputs:
- transferred heat
- available heat
- boiler efficiency
- closure check

### 2. Design workflow

Use when the user wants the program to estimate missing performance values from a chosen design focus.

Typical waste heat boiler inputs:
- exhaust composition
- exhaust inlet temperature
- exhaust mass flow
- selected thermal oil
- oil inlet temperature
- oil mass flow
- one chosen design driver

The design workflow should not solve from underdefined inputs.
At least one governing target or constraint must be selected by the user.

For the first release, the selectable waste heat boiler design drivers should be:
- minimum stack temperature
- target boiler efficiency
- target oil outlet temperature
- target transferred power
- exchanger effectiveness or UA
- minimum pinch approach

The selected design driver becomes part of the calculation basis and result metadata.

## First-release ORC simplification

For the first release, do not force a detailed turbine, pump, and phase-resolved cycle model.

Instead:
- calculate heat taken from thermal oil
- calculate ORC absorbed heat
- calculate working-fluid temperature gain only in supported screening mode
- estimate gross electric power from absorbed ORC heat
- report explicit screening efficiency basis

If a requested working-fluid path cannot be supported safely in temperature-based screening mode, block that path and require duty-based screening or later detailed modeling.

## First KPI definitions

Use these names consistently:

- `Q_exhaust_available`
  - heat available in the exhaust above the chosen minimum stack temperature
- `Q_boiler_transferred`
  - heat released by exhaust and transferred through the waste heat boiler
- `Q_oil_absorbed`
  - heat gained by thermal oil
- `Q_orc_absorbed`
  - heat absorbed by the ORC working fluid across its heater train
- `P_gross_electric`
  - gross electric output at generator terminals
- `P_net_electric`
  - gross electric output minus pumps, fans, and other internal loads

Efficiency definitions:
- `eta_boiler = Q_oil_absorbed / Q_exhaust_available`
- `eta_orc_gross = P_gross_electric / Q_orc_absorbed`
- `eta_system_gross = P_gross_electric / Q_exhaust_available`
- `eta_system_net = P_net_electric / Q_exhaust_available`

Do not reuse a single label like `efficiency` without naming its basis.

## First-principles energy balances

### 1. Exhaust available heat

`Q_exhaust_available = m_dot_exh * integral(cp_exh_mix(T) dT, T_stack_min to T_exh_in)`

First-pass approximation when a validated average heat capacity is acceptable:

`Q_exhaust_available ~= m_dot_exh * cp_exh_avg * (T_exh_in - T_stack_min)`

### 2. Heat released by exhaust across the boiler

`Q_boiler_transferred = m_dot_exh * integral(cp_exh_mix(T) dT, T_exh_out to T_exh_in)`

### 3. Heat absorbed by thermal oil

`Q_oil_absorbed = m_dot_oil * integral(cp_oil(T) dT, T_oil_out to T_oil_in)`

Use signed implementation carefully; user-facing reporting should display positive absorbed heat.

Equivalent magnitude form:

`Q_oil_absorbed = m_dot_oil * integral(cp_oil(T) dT, T_oil_in to T_oil_out)`

### 3A. Design-driver examples for the waste heat boiler

If minimum stack temperature is selected:

`Q_exhaust_available = m_dot_exh * integral(cp_exh_mix(T) dT, T_stack_min to T_exh_in)`

If target boiler efficiency is selected:

`Q_target = eta_boiler_target * Q_exhaust_available`

If target oil outlet temperature is selected:

`Q_target = m_dot_oil * integral(cp_oil(T) dT, T_oil_in to T_oil_out_target)`

If target transferred power is selected:

`Q_target = Q_transferred_target`

If exchanger effectiveness is selected:

`Q_target = effectiveness * Q_max`

If a UA-based method is selected later:

`Q_target = UA * LMTD`

If minimum pinch approach is selected:
- solve the exchanger with the pinch condition enforced at the limiting end
- block the result if the requested duty violates the selected minimum pinch

### 4. Heat absorbed by ORC working fluid

`Q_orc_absorbed = sum(Q_stage_i)`

For a single heater:

`Q_orc_absorbed = m_dot_wf * (h_wf_out - h_wf_in)`

For staged heating:
- preheater duty
- evaporator duty
- superheater duty
- optional recuperator contribution reported separately

### 5. Screening ORC temperature gain

For supported single-phase screening cases:

`delta_t_wf = T_wf_out - T_wf_in`

If a validated average heat capacity is available and the path is single phase:

`Q_orc_absorbed ~= m_dot_wf * cp_wf_avg * delta_t_wf`

If the path is not safely supported by a screening property method, do not fake a temperature-only result.

### 6. Screening gross electric power basis

For the first release:

`P_gross_electric = eta_orc_gross_screening * Q_orc_absorbed`

Or, when gross power is known from plant data:

`eta_orc_gross_screening = P_gross_electric / Q_orc_absorbed`

### 7. Future detailed turbine and pump power basis

Detailed cycle formulas will be frozen later, but the reporting basis should remain:

- `W_turbine = m_dot_wf * (h_turb_in - h_turb_out_actual)`
- `W_pump = m_dot_wf * (h_pump_out_actual - h_pump_in)`
- `P_gross_electric = eta_mech_gen * W_turbine`
- `P_net_electric = P_gross_electric - P_pump - P_aux`

## Required validation rules

Always validate at least:
- mass flows are positive
- fraction sums close to one
- hot-side inlet temperature is greater than hot-side outlet temperature
- cold-side outlet temperature is greater than cold-side inlet temperature when heating is expected
- minimum pinch or approach temperature remains positive
- stack temperature is not driven below the selected limit
- oil maximum bulk temperature is not exceeded
- phase/state requests are compatible with the chosen property backend
- unsupported ORC two-phase paths are blocked in simplified temperature mode
- solved heat duty does not exceed the physically available upstream heat
- energy closure error remains within the configured tolerance

## Property strategy

Preferred direction:
- exhaust gas mixture: `Cantera` or another validated mixture-capable path
- working fluid and many pure-fluid states: `CoolProp`
- supporting engineering correlations and constants: `thermo`, `chemicals`, `ht`

Do not lock the whole application to a single property tool if that tool is weak for one part of the plant.

## Calculation trace contract

Every important solve result should expose enough detail to answer:
- what inputs were used
- what assumptions were applied
- which backend supplied the properties
- which equations or mode were used
- why a warning or blocked state was triggered

## Benchmark expectation

Before the product is trusted, compare key solver outputs against at least one of:
- known plant data
- vendor thermal-oil data
- hand calculations
- literature examples
- prior validated internal cases
