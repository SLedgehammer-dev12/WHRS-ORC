# ToDo

## Priority 1 - lock the engineering basis

- [x] Create `DOMAIN_MODEL.md`.
- [x] Create `EQUIPMENT_CONTRACTS.md`.
- [x] Define `RESULT_SCHEMA.md`.
- [x] Define `VALIDATION_RULES.md`.
- [x] Define `TEST_STRATEGY.md`.
- [ ] Freeze KPI definitions and naming for gross vs net power.
- [ ] Define minimum validation rules for pinch, stack temperature, closure error, and oil limits.
- [ ] Decide first-release property backend matrix.

## Priority 2 - prepare data and references

- [ ] Build a fluid-data inventory from `HRS ORC/` and `HRS ORC Version 2/`.
- [ ] Define thermal-oil catalog format and source traceability fields.
- [ ] Define exhaust-gas composition presets and manual-entry rules.
- [x] Collect at least 3 benchmark study cases for regression testing.

## Priority 3 - prepare implementation contracts

- [x] Define result schema with values, warnings, assumptions, calc_trace, and blocked state.
- [x] Create `EXHAUST_BOILER_CODE_READY_SPEC.md`.
- [ ] Define the first equipment modules:
  - [x] exhaust source
  - [x] waste heat boiler
  - [x] thermal-oil loop
  - [x] ORC screening heat/power block
- [x] Add plant-level screening orchestration.
- [x] Define logging schema and report metadata fields.
- [x] Decide persistence model for saved cases.

## Priority 4 - prepare product experience

- [x] Sketch quick screening UX.
- [x] Sketch detailed flowsheet UX.
- [x] Decide whether the live process diagram should evolve into an interactive detailed flowsheet.
- [ ] Decide which remaining non-visual inputs should also move onto the process diagram:
  - [ ] fluid property override fields
- [x] Define report sections and export priorities.
- [x] Decide the first application shell.
- [x] Add blocked-state surfacing and operator guidance in the UI shell.
- [x] Add benchmark/preset case loading in the UI shell.
- [x] Add report/export actions in the UI shell.
- [x] Add animated flow direction and click-to-inspect equipment details to the process diagram.
