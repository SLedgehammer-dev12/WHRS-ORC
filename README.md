# WHRS ORC

WHRS ORC is a calculation-first engineering application for screening a gas-turbine waste-heat recovery system:

- gas turbine exhaust
- waste heat boiler / thermal-oil heater
- thermal-oil transport loop
- ORC screening heat uptake
- ORC screening gross electric power

The current release focuses on trustworthy thermal balances, blocked-state handling for non-physical cases, and an operator-friendly desktop UI.

## Current scope

- Exhaust-gas composition entry with validation
- Waste heat boiler performance and selected design-driver modes
- Thermal-oil loop screening transport
- ORC heat uptake screening
- ORC gross power screening
- Interactive process diagram with unit-aware input cards
- Operator guidance for warnings and blocked states
- Benchmark case loading
- Saved-case load and save flow with `.whrs.json` files
- Structured screening run logging to `data/logs/screening_runs.jsonl`
- Markdown and JSON report export

## Run the app

```powershell
python app.py
```

## Run the tests

```powershell
python -m unittest discover -s tests
```

## Project structure

```text
WHRS ORC/
  app.py
  src/whrs_orc/
  tests/
  data/
  skills/
  README.md
  CHANGELOG.md
```

## Engineering direction

- Calculation correctness first
- Explicit warnings, assumptions, and blocked states
- Quick screening before detailed ORC turbomachinery
- `HRS ORC Version 2` is used only as a property/data reference source where needed

## Current version

- `0.2.0`
