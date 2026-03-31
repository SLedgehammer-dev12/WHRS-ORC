# Changelog

## Unreleased

- Added animated flow particles to the live process diagram.
- Added clickable equipment detail inspection on the schematic.
- Added pure helper modules for stream motion and equipment-detail rendering.
- Expanded test coverage for stream-motion math and equipment-detail summaries.
- Added a multi-stage ORC heater train model with mode-dependent stage inputs.
- Corrected the thermal-oil routing between boiler and ORC heater in the UI schematic.
- Added persistence and report payload support for stage-based ORC heater definitions.

## 0.2.0 - 2026-03-30

- Added benchmark case loading for repeatable screening studies.
- Added Markdown report export and JSON bundle export.
- Added a reporting layer for packaging solved case data.
- Added operator guidance panel content to exported reports.
- Tightened waste heat boiler validation so negative minimum temperature approach blocks the solution.
- Added operator-facing suggested actions for blocked boiler cases.
- Expanded test coverage to benchmark cases and reporting helpers.

## 0.1.0 - 2026-03-29

- Created the first screening solver backbone for exhaust, boiler, thermal oil loop, ORC heat uptake, and ORC gross power.
- Added the first desktop UI shell with interactive process diagram.
- Added calculation/result schema, validation rules, and baseline engineering documents.
