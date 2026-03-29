from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from whrs_orc.domain.models import CompositionBasis, FluidLimitSpec, ProcessStream


class ValidationAction(StrEnum):
    BLOCK = "block"
    HARD_WARNING = "hard_warning"
    SOFT_WARNING = "soft_warning"
    INFO = "info"


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    action: ValidationAction
    source: str


def validate_composition_sum(stream: ProcessStream, *, tolerance: float = 1e-4) -> list[ValidationIssue]:
    composition = stream.fluid.composition
    if composition is None or not composition.components:
        return []
    total = sum(component.fraction for component in composition.components)
    issues: list[ValidationIssue] = []
    if composition.basis is not CompositionBasis.MOLE_FRACTION:
        issues.append(
            ValidationIssue(
                code="VAL-COMP-002",
                message="Only mole-fraction exhaust composition is supported in the first implementation pass.",
                action=ValidationAction.BLOCK,
                source="composition",
            )
        )
    if abs(total - 1.0) > tolerance:
        issues.append(
            ValidationIssue(
                code="VAL-COMP-001",
                message=f"Composition fractions must sum to 1.0 +/- {tolerance:g}. Current total is {total:.6f}.",
                action=ValidationAction.BLOCK,
                source="composition",
            )
        )
    if any(component.fraction < 0.0 for component in composition.components):
        issues.append(
            ValidationIssue(
                code="VAL-COMP-003",
                message="Composition fractions cannot be negative.",
                action=ValidationAction.BLOCK,
                source="composition",
            )
        )
    return issues


def validate_positive_mass_flow(stream: ProcessStream) -> list[ValidationIssue]:
    if stream.mass_flow_kg_s > 0.0:
        return []
    return [
        ValidationIssue(
            code="VAL-FLOW-001",
            message=f"Mass flow for stream `{stream.stream_id}` must be strictly positive.",
            action=ValidationAction.BLOCK,
            source="stream",
        )
    ]


def validate_state_temperature(temp_k: float | None, *, source: str) -> list[ValidationIssue]:
    if temp_k is None:
        return [
            ValidationIssue(
                code="VAL-TEMP-000",
                message=f"Temperature is required for `{source}`.",
                action=ValidationAction.BLOCK,
                source=source,
            )
        ]
    if temp_k <= 0.0:
        return [
            ValidationIssue(
                code="VAL-TEMP-001",
                message=f"Temperature for `{source}` must be above absolute zero.",
                action=ValidationAction.BLOCK,
                source=source,
            )
        ]
    return []


def validate_pressure(pressure_pa: float | None, *, source: str) -> list[ValidationIssue]:
    if pressure_pa is None:
        return []
    if pressure_pa > 0.0:
        return []
    return [
        ValidationIssue(
            code="VAL-PRES-001",
            message=f"Pressure for `{source}` must be strictly positive.",
            action=ValidationAction.BLOCK,
            source=source,
        )
    ]


def validate_hot_cold_temperature_order(
    hot_in_k: float,
    hot_out_k: float,
    cold_in_k: float,
    cold_out_k: float,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if hot_in_k <= hot_out_k:
        issues.append(
            ValidationIssue(
                code="VAL-HX-001",
                message="Hot-side inlet temperature must be greater than hot-side outlet temperature.",
                action=ValidationAction.BLOCK,
                source="heat_exchanger",
            )
        )
    if cold_out_k <= cold_in_k:
        issues.append(
            ValidationIssue(
                code="VAL-HX-002",
                message="Cold-side outlet temperature must be greater than cold-side inlet temperature.",
                action=ValidationAction.BLOCK,
                source="heat_exchanger",
            )
        )
    return issues


def validate_minimum_temperature_approach(
    min_delta_t_k: float,
    *,
    minimum_delta_t_k: float = 0.0,
    source: str = "heat_exchanger",
) -> list[ValidationIssue]:
    if min_delta_t_k >= minimum_delta_t_k:
        return []
    return [
        ValidationIssue(
            code="VAL-HX-003",
            message=(
                "Resolved minimum hot-cold temperature approach is below the required threshold. "
                f"Current value is {min_delta_t_k:.3f} K and required minimum is {minimum_delta_t_k:.3f} K."
            ),
            action=ValidationAction.BLOCK,
            source=source,
        )
    ]


def validate_stack_floor(exhaust_outlet_k: float, stack_min_k: float) -> list[ValidationIssue]:
    if exhaust_outlet_k >= stack_min_k:
        return []
    return [
        ValidationIssue(
            code="VAL-STACK-001",
            message="Resolved stack temperature falls below the configured minimum stack temperature.",
            action=ValidationAction.BLOCK,
            source="boiler",
        )
    ]


def validate_fluid_limit(temp_k: float, limits: FluidLimitSpec | None, *, source: str) -> list[ValidationIssue]:
    if limits is None:
        return []
    issues: list[ValidationIssue] = []
    if limits.min_bulk_temp_k is not None and temp_k < limits.min_bulk_temp_k:
        issues.append(
            ValidationIssue(
                code="VAL-LIMIT-LOW",
                message=f"Temperature for `{source}` is below the configured fluid minimum bulk temperature.",
                action=ValidationAction.BLOCK,
                source=source,
            )
        )
    if limits.max_bulk_temp_k is not None and temp_k > limits.max_bulk_temp_k:
        issues.append(
            ValidationIssue(
                code="VAL-OIL-001",
                message=f"Temperature for `{source}` exceeds the configured fluid maximum bulk temperature.",
                action=ValidationAction.BLOCK,
                source=source,
            )
        )
    return issues


def validate_single_design_driver(selected_count: int) -> list[ValidationIssue]:
    if selected_count == 1:
        return []
    return [
        ValidationIssue(
            code="VAL-BOILER-003",
            message="Exactly one governing design driver must be selected in design mode.",
            action=ValidationAction.BLOCK,
            source="boiler_design",
        )
    ]
