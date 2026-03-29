# Test Strategy

## Purpose

This document defines how testing will be planned and attached to every code-generation step in WHRS ORC.

## Core rule

No meaningful code addition is complete until its planned tests are defined.

For every coding step we should record:
- what changed
- what tests were added or updated
- what was run
- what remains intentionally untested

## Test layers

### 1. Schema tests

Use for:
- domain objects
- result schema
- serialization rules

Typical checks:
- required fields
- SI-unit expectations
- invalid payload rejection

### 2. Validator tests

Use for:
- input checks
- blocked-state triggers
- warning thresholds

Typical checks:
- composition sum failures
- negative flow rejection
- temperature ordering rejection
- stack limit rejection

### 3. Calculation unit tests

Use for:
- deterministic equations
- constant-property benchmark cases
- energy-balance calculations

Typical checks:
- available heat from known `cp`
- boiler duty balance
- ORC screening gross-power conversion

### 4. Regression benchmark tests

Use for:
- previously trusted engineering cases
- saved benchmark studies
- bug-fix protection

Typical checks:
- known exhaust-source case
- known boiler performance case
- known ORC screening case

### 5. Integration tests

Use for:
- linked equipment modules
- result-envelope propagation
- warnings and blocked-state propagation across modules

## Test-first planning requirement for each coding step

Before implementing a module, define:
1. happy-path tests
2. boundary tests
3. blocked-state tests
4. regression tests if prior behavior exists

## First test matrix by module

### Domain model
- valid object creation
- missing required field rejection
- unit-field naming consistency

### Result schema
- required envelope fields
- blocked-state envelope
- warning and assumption persistence
- serialization round-trip

### Validation rules
- one pass case and one fail case per blocking rule
- threshold-edge cases for warning levels

### Exhaust source
- constant-`cp` available-heat case
- outlet-temperature released-heat case
- stack-floor block case
- composition-sum block case

### Waste heat boiler
- oil absorbed heat case
- boiler efficiency case
- closure-ratio warning case
- oil temperature limit block case
- impossible duty block case
- design mode with minimum stack temperature case
- design mode with target boiler efficiency case
- design mode with target oil outlet temperature case
- design mode missing driver block case
- design mode multiple-driver ambiguity block case

### ORC screening heat and power block
- oil-to-ORC heat transfer case
- working-fluid temperature-gain case for supported single-phase mode
- gross-power from efficiency case
- gross-efficiency back-calculation case
- unsupported two-phase temperature-mode block case

## File naming direction

Recommended first test files:
- `tests/test_domain_models.py`
- `tests/test_result_schema.py`
- `tests/test_validation_rules.py`
- `tests/test_exhaust_source.py`
- `tests/test_waste_heat_boiler.py`
- `tests/test_orc_screening.py`

## Session discipline

Whenever code is written:
- mention the intended tests before or during implementation
- run the relevant tests when possible
- record test status in `SESSION_HANDOFF.md`

## Acceptable temporary gaps

If a test cannot yet be automated, record:
- why it is blocked
- what manual check was used
- what future automated test should replace it
