# Continuity

Last updated: 2026-03-30

## Project intent

WHRS ORC is a new engineering application for a compressor-station waste heat recovery plant:
- gas turbine exhaust transfers heat to thermal oil
- thermal oil transfers heat to the ORC working fluid
- the ORC generator produces electric power

The project priority is calculation correctness first, then operator usability, then delivery polish.

## Agreed direction so far

- Planning must be completed before major coding begins.
- `WHRS ORC/` is the new working folder.
- `HRS ORC/` and `HRS ORC Version 2/` may be used as requirement and architecture references.
- The new project should borrow what is useful from earlier work, but remain free to adopt a cleaner structure.
- The application should support:
  - quick screening calculations
  - detailed thermal calculations
  - reportable engineering studies
  - traceable warnings, assumptions, and calculation logs

## Architecture decisions made in this session

- The project will follow a calculation-first, validation-first architecture.
- Internal units will remain SI across the model layer.
- The system will be layered as:
  - domain and contracts
  - property services
  - equipment models
  - solver orchestration
  - reporting, logging, and persistence
  - UI adapters
- Root planning documents were created to control continuity from the first session.
- The first stable contract documents now exist:
  - `DOMAIN_MODEL.md`
  - `EQUIPMENT_CONTRACTS.md`
- The common result and validation baseline now exists:
  - `RESULT_SCHEMA.md`
  - `VALIDATION_RULES.md`
  - `TEST_STRATEGY.md`
- The first code-ready module spec now exists:
  - `EXHAUST_BOILER_CODE_READY_SPEC.md`
- The first implementation pass now exists for:
  - domain models
  - result schema
  - validation helpers
  - exhaust property provider
  - thermal-oil property provider
  - exhaust source solver
  - waste heat boiler solver
  - first unit-test suite
- The next screening-level implementation slice now exists for:
  - thermal-oil loop solver
  - working-fluid screening property provider
  - ORC screening heat-uptake solver
  - ORC screening gross-power solver
  - expanded unit-test suite
- The first plant-level screening orchestration now exists:
  - `screening_case.py` chains boiler, thermal-oil loop, ORC heat uptake, and ORC gross power
  - the hot-oil handoff from boiler to loop was corrected to use the resolved boiler outlet state
- The first desktop UI shell now exists:
  - `tkinter`-based quick screening studio
  - mode-aware form behavior for performance vs design studies
  - dynamic enable/disable logic for boiler driver, loop mode, ORC heat mode, and ORC power mode
  - KPI cards plus input snapshot, summary, and diagnostics tabs
  - a canvas-based live process diagram inspired by the reference ORC schematic supplied by the user
  - equipment-level stage summaries mapped from screening results
  - process-condition cards on the diagram itself so key values can be entered near the relevant equipment
  - per-card unit selectors with conversion to the app's canonical calculation units
  - a larger and more detailed diagram layout where cards sit near the relevant equipment but do not cover the schematic
  - exhaust composition entry and design-target entry are now also represented on the diagram
  - composition-total feedback is shown directly in the UI to reduce invalid gas-mixture entry risk
- UI behavior rules were extracted into a pure helper layer:
  - `ui/view_model.py`
  - covered by dedicated unit tests
- Process-diagram content rules were also extracted into a pure helper layer:
  - `ui/process_diagram.py`
  - covered by dedicated unit tests
- Diagram-unit conversion rules were extracted into a pure helper layer:
  - `ui/diagram_units.py`
  - covered by dedicated unit tests
- Operator-guidance rules were extracted into a pure helper layer:
  - `ui/operator_guidance.py`
  - covered by dedicated unit tests
- Benchmark-case library rules were extracted into a pure helper layer:
  - `ui/benchmark_cases.py`
  - covered by dedicated unit tests
- Report assembly rules were extracted into a pure helper layer:
  - `reporting/screening_report.py`
  - covered by dedicated unit tests
- Saved-case persistence rules were extracted into a pure helper layer:
  - `persistence/saved_cases.py`
  - covered by dedicated unit tests
- Structured solve-log rules were extracted into a pure helper layer:
  - `logging/run_logger.py`
  - covered by dedicated unit tests
- Stream palette and fluid-visual rules were extracted into a pure helper layer:
  - `ui/stream_palette.py`
  - covered by dedicated unit tests
- The ORC side is intentionally simplified for the first release:
  - calculate absorbed ORC heat
  - calculate supported working-fluid temperature gain
  - estimate gross electric power from absorbed heat
  - defer detailed pump/turbine modeling
- Waste heat boiler design mode is now defined as user-driven:
  - the user selects the governing design target
  - the first candidate targets are stack temperature, boiler efficiency, oil outlet temperature, transferred power, effectiveness or UA, and minimum pinch approach
- `HRS ORC Version 2` is now treated only as a property/data reference source for:
  - exhaust gas component seeds
  - thermal-oil catalog seeds
  It is no longer a reference for solver structure or UI decisions.
- Waste heat boiler validation is now intentionally stricter:
  - a negative minimum hot-cold approach is treated as a blocked non-physical point
  - the blocked result carries operator-facing recovery guidance for the UI
- The desktop UI now supports:
  - loading prepared benchmark cases directly into the form
  - saving and loading `.whrs.json` case files
  - exporting a Markdown study report
  - exporting a JSON bundle with case inputs, guidance, KPIs, and result envelopes
  - automatically appending screening run logs to `data/logs/screening_runs.jsonl`
  - a larger and more detailed process schematic
  - fluid-specific cold-to-hot palettes for exhaust gas, thermal oil, and working fluid
  - palette legend ramps so users can distinguish fluids without color confusion
- The root folder now includes release-readiness files:
  - `README.md`
  - `CHANGELOG.md`
  - `.gitignore`
  - `pyproject.toml`
- The project now also has a published public GitHub home:
  - repository: `https://github.com/SLedgehammer-dev12/WHRS-ORC`
  - tagged release: `v0.2.0`
  - uploaded release asset: `whrs-orc-v0.2.0.zip`
- Two project-local skills were created:
  - `whrs-orc-architect`
  - `whrs-orc-thermal-calculation-guardian`
- The initial folder skeleton was created under:
  - `src/whrs_orc/`
  - `data/`
  - `tests/`
  - `skills/`

## Current baseline

The baseline now includes:
- project instructions
- continuity tracking
- architecture planning
- calculation basis
- domain contracts
- equipment contracts
- common result schema
- common validation rules
- test strategy
- first code-ready module spec
- first working code for the exhaust and boiler backbone
- first working code for the thermal-oil loop and ORC screening backbone
- first working code for plant-level screening orchestration
- first working desktop UI shell
- handoff notes
- actionable TODO list
- project skill skeletons

## Immediate next best step

Translate the current screening baseline into a more complete engineering product:
1. decide the first property-backend matrix for:
   - exhaust gas
   - thermal oil
   - ORC working fluid
2. prepare benchmark cases and validation thresholds
3. add saved benchmark datasets and reference cases to the test suite
4. begin the next implementation slice:
    - deeper interaction over the process diagram if the desktop shell remains the chosen path
    - decide whether manual fluid-property overrides should also move onto the diagram
    - maintain release discipline for future tags now that the first public repo and release exist
    - define backward-compatibility rules for future saved-case schema changes
    - decide whether export and solve logs should gain richer plant/site metadata
    - add animated flow direction and equipment detail interactions on top of the new palette-aware schematic

## Open decisions

- Which ORC working fluids will be in first release scope.
- Whether the first coded release ends at gross generator power or also includes net-power parasitics.
- Whether the first production UI should remain `tkinter` or later move to PySide6 after the solver/reporting layer stabilizes.
- Which exhaust-gas property path becomes the primary backend:
  - Cantera-first
  - thermo/chemicals-first
  - simplified validated cp tables for early screening
- Which site defaults are required for stack temperature, oil-film limits, and minimum pinch margins.

## Session rule

Whenever project direction changes, update this file before ending the session.
