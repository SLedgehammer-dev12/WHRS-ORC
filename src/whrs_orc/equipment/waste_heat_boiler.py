from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from whrs_orc.domain.models import FluidKind, StatePoint
from whrs_orc.domain.result_schema import (
    AssumptionRecord,
    CalcTraceEntry,
    MetricValue,
    ResultEnvelope,
    ResultStatus,
    WarningRecord,
    WarningSeverity,
)
from whrs_orc.equipment.contracts import BoilerDesignDriver, BoilerMode, WasteHeatBoilerRequest
from whrs_orc.properties.exhaust_properties import ExhaustPropertyProvider
from whrs_orc.properties.thermal_oil_properties import ThermalOilPropertyProvider
from whrs_orc.solvers.validation_rules import (
    ValidationAction,
    validate_composition_sum,
    validate_fluid_limit,
    validate_hot_cold_temperature_order,
    validate_minimum_temperature_approach,
    validate_positive_mass_flow,
    validate_state_temperature,
)


MODEL_NAME = "waste_heat_boiler"
MODEL_VERSION = "0.1.0"


def solve_waste_heat_boiler(
    request: WasteHeatBoilerRequest,
    *,
    exhaust_provider: ExhaustPropertyProvider | None = None,
    oil_provider: ThermalOilPropertyProvider | None = None,
) -> ResultEnvelope:
    exhaust_provider = exhaust_provider or ExhaustPropertyProvider()
    oil_provider = oil_provider or ThermalOilPropertyProvider()

    issues = []
    issues.extend(validate_positive_mass_flow(request.exhaust_stream))
    issues.extend(validate_positive_mass_flow(request.oil_stream))
    issues.extend(validate_state_temperature(request.exhaust_stream.inlet.temp_k, source="exhaust_inlet"))
    issues.extend(validate_state_temperature(request.oil_stream.inlet.temp_k, source="oil_inlet"))
    issues.extend(validate_composition_sum(request.exhaust_stream))

    if request.exhaust_stream.fluid.kind is not FluidKind.EXHAUST_GAS:
        return _blocked("VAL-KIND-EXH", "Waste heat boiler requires an exhaust-gas hot stream.", request)
    if request.oil_stream.fluid.kind is not FluidKind.THERMAL_OIL:
        return _blocked("VAL-KIND-OIL", "Waste heat boiler requires a thermal-oil cold stream.", request)

    blocking = [issue for issue in issues if issue.action is ValidationAction.BLOCK]
    if blocking:
        first = blocking[0]
        return _blocked(first.code, first.message, request, source=first.source)

    if request.mode is BoilerMode.PERFORMANCE:
        return _solve_performance(request, exhaust_provider, oil_provider)
    if request.mode is BoilerMode.DESIGN:
        return _solve_design(request, exhaust_provider, oil_provider)
    return _blocked("VAL-MODE-001", f"Unsupported boiler mode `{request.mode}`.", request)


def _solve_performance(
    request: WasteHeatBoilerRequest,
    exhaust_provider: ExhaustPropertyProvider,
    oil_provider: ThermalOilPropertyProvider,
) -> ResultEnvelope:
    if request.exhaust_stream.outlet is None or request.exhaust_stream.outlet.temp_k is None:
        return _blocked("VAL-OUTLET-EXH", "Performance mode requires exhaust outlet temperature.", request)
    if request.oil_stream.outlet is None or request.oil_stream.outlet.temp_k is None:
        return _blocked("VAL-OUTLET-OIL", "Performance mode requires oil outlet temperature.", request)
    if request.constraints.stack_min_temp_k is None:
        return _blocked("VAL-STACK-REQ", "Performance mode requires stack minimum temperature.", request)

    exhaust_in_k = request.exhaust_stream.inlet.temp_k
    exhaust_out_k = request.exhaust_stream.outlet.temp_k
    oil_in_k = request.oil_stream.inlet.temp_k
    oil_out_k = request.oil_stream.outlet.temp_k
    assert exhaust_in_k is not None and exhaust_out_k is not None and oil_in_k is not None and oil_out_k is not None

    ordering_issues = validate_hot_cold_temperature_order(exhaust_in_k, exhaust_out_k, oil_in_k, oil_out_k)
    if ordering_issues:
        first = ordering_issues[0]
        return _blocked(first.code, first.message, request, source=first.source)
    if exhaust_out_k < request.constraints.stack_min_temp_k:
        return _blocked("VAL-STACK-001", "Resolved stack temperature falls below the configured minimum stack temperature.", request)

    oil_limits = request.oil_stream.fluid.limits or oil_provider.limits(request.oil_stream.fluid)
    oil_limit_issues = validate_fluid_limit(oil_out_k, oil_limits, source="oil_outlet")
    if oil_limit_issues:
        first = oil_limit_issues[0]
        return _blocked(first.code, first.message, request, source=first.source)

    q_available = request.exhaust_stream.mass_flow_kg_s * exhaust_provider.heat_release_j_kg(
        request.exhaust_stream.fluid,
        exhaust_in_k,
        request.constraints.stack_min_temp_k,
        request.exhaust_stream.inlet.pressure_pa,
    ).value
    q_gas = request.exhaust_stream.mass_flow_kg_s * exhaust_provider.heat_release_j_kg(
        request.exhaust_stream.fluid,
        exhaust_in_k,
        exhaust_out_k,
        request.exhaust_stream.inlet.pressure_pa,
    ).value
    q_oil = request.oil_stream.mass_flow_kg_s * oil_provider.heat_gain_j_kg(
        request.oil_stream.fluid,
        oil_in_k,
        oil_out_k,
    ).value

    if q_oil > q_available * (1.0 + request.constraints.max_closure_fraction):
        return _blocked("VAL-BOILER-001", "Thermal-oil absorbed heat exceeds physically available exhaust heat.", request)

    eta_boiler = q_oil / q_available if q_available > 0.0 else 0.0
    closure_error = q_gas - q_oil
    closure_ratio = closure_error / max(abs(q_gas), abs(q_oil), 1.0)
    min_delta_t = min(exhaust_in_k - oil_out_k, exhaust_out_k - oil_in_k)
    minimum_required_delta_t = request.constraints.min_pinch_delta_t_k or 0.0
    approach_issues = validate_minimum_temperature_approach(
        min_delta_t,
        minimum_delta_t_k=minimum_required_delta_t,
        source="boiler",
    )
    if approach_issues:
        first = approach_issues[0]
        return _blocked(
            first.code,
            first.message,
            request,
            source=first.source,
            suggested_action=(
                "Increase exhaust outlet temperature, reduce oil-side duty, or review the measured oil and exhaust temperatures for the same operating point."
            ),
        )

    result = _base_boiler_result(request)
    _add_boiler_metrics(result, q_available, q_gas, q_oil, eta_boiler, closure_error, closure_ratio, min_delta_t)
    result.solved_streams["resolved_exhaust_stream"] = request.exhaust_stream
    result.solved_streams["resolved_oil_stream"] = request.oil_stream
    result.metadata.update({"calculation_mode": request.mode, "design_driver": None})
    result.assumptions.append(
        AssumptionRecord(
            code="ASM-BOILER-001",
            message="Performance mode uses entered hot-side and cold-side outlet temperatures.",
            source="waste_heat_boiler",
        )
    )
    result.calc_trace.append(
        CalcTraceEntry(
            step="performance_balance",
            message="Calculated available heat, exhaust-side release, oil absorbed heat, and closure.",
            value_snapshot={
                "q_available_w": q_available,
                "q_gas_w": q_gas,
                "q_oil_w": q_oil,
                "closure_ratio": closure_ratio,
                "min_delta_t_k": min_delta_t,
            },
        )
    )
    _maybe_add_closure_warning(result, request, closure_ratio)
    return result


def _solve_design(
    request: WasteHeatBoilerRequest,
    exhaust_provider: ExhaustPropertyProvider,
    oil_provider: ThermalOilPropertyProvider,
) -> ResultEnvelope:
    if request.design_target is None:
        return _blocked("VAL-BOILER-003", "Design mode requires exactly one governing design driver.", request, source="boiler_design")

    exhaust_in_k = request.exhaust_stream.inlet.temp_k
    oil_in_k = request.oil_stream.inlet.temp_k
    assert exhaust_in_k is not None and oil_in_k is not None

    driver = request.design_target.design_driver
    target = request.design_target.target_value_si
    oil_limits = request.oil_stream.fluid.limits or oil_provider.limits(request.oil_stream.fluid)
    max_oil_k = request.constraints.max_oil_bulk_temp_k or (oil_limits.max_bulk_temp_k if oil_limits is not None else None)

    stack_basis_k = request.constraints.stack_min_temp_k
    if driver is BoilerDesignDriver.MINIMUM_STACK_TEMPERATURE:
        stack_basis_k = target
    if stack_basis_k is None:
        return _blocked(
            "VAL-STACK-REQ",
            "Design mode requires a stack minimum basis or the minimum-stack-temperature design driver.",
            request,
        )
    if exhaust_in_k <= stack_basis_k:
        return _blocked("VAL-STACK-001", "Exhaust inlet temperature must be above the selected stack minimum temperature.", request)

    q_available = request.exhaust_stream.mass_flow_kg_s * exhaust_provider.heat_release_j_kg(
        request.exhaust_stream.fluid,
        exhaust_in_k,
        stack_basis_k,
        request.exhaust_stream.inlet.pressure_pa,
    ).value

    if driver is BoilerDesignDriver.MINIMUM_STACK_TEMPERATURE:
        q_target = q_available
        exhaust_out_k = stack_basis_k
        design_basis = "Transferred heat is governed by available exhaust heat above the selected stack floor."
    elif driver is BoilerDesignDriver.TARGET_BOILER_EFFICIENCY:
        if not 0.0 <= target <= 1.0:
            return _blocked("VAL-BOILER-004", "Target boiler efficiency must be between 0 and 1.", request, source="boiler_design")
        q_target = target * q_available
        exhaust_out_k, achieved_q_per_kg = exhaust_provider.solve_outlet_temp_k(
            request.exhaust_stream.fluid,
            exhaust_in_k,
            q_target / request.exhaust_stream.mass_flow_kg_s,
            pressure_pa=request.exhaust_stream.inlet.pressure_pa,
            minimum_temp_k=stack_basis_k,
        )
        q_target = achieved_q_per_kg * request.exhaust_stream.mass_flow_kg_s
        design_basis = "Transferred heat is governed by the selected target boiler efficiency."
    elif driver is BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE:
        if target <= oil_in_k:
            return _blocked("VAL-BOILER-004", "Target oil outlet temperature must be greater than oil inlet temperature.", request, source="boiler_design")
        if max_oil_k is not None and target > max_oil_k:
            return _blocked("VAL-OIL-001", "Target oil outlet temperature exceeds the oil bulk temperature limit.", request)
        q_target = request.oil_stream.mass_flow_kg_s * oil_provider.heat_gain_j_kg(
            request.oil_stream.fluid,
            oil_in_k,
            target,
        ).value
        exhaust_out_k, achieved_q_per_kg = exhaust_provider.solve_outlet_temp_k(
            request.exhaust_stream.fluid,
            exhaust_in_k,
            q_target / request.exhaust_stream.mass_flow_kg_s,
            pressure_pa=request.exhaust_stream.inlet.pressure_pa,
            minimum_temp_k=stack_basis_k,
        )
        q_target = achieved_q_per_kg * request.exhaust_stream.mass_flow_kg_s
        design_basis = "Transferred heat is governed by the selected oil outlet temperature target."
    else:
        return _blocked(
            "VAL-BOILER-005",
            f"Design driver `{driver}` is planned but not implemented in the first coding pass.",
            request,
            source="boiler_design",
        )

    if q_target > q_available * (1.0 + request.constraints.max_closure_fraction):
        return _blocked("VAL-BOILER-001", "Requested design duty exceeds available exhaust heat.", request)

    oil_out_k, achieved_oil_q_per_kg = oil_provider.solve_outlet_temp_k(
        request.oil_stream.fluid,
        oil_in_k,
        q_target / request.oil_stream.mass_flow_kg_s,
        upper_bound_temp_k=max_oil_k,
    )
    q_oil = achieved_oil_q_per_kg * request.oil_stream.mass_flow_kg_s
    if max_oil_k is not None and oil_out_k >= max_oil_k and q_oil + 1.0 < q_target:
        return _blocked("VAL-OIL-001", "Required design duty exceeds the allowed oil bulk temperature limit.", request)

    q_gas = min(q_target, q_available)
    eta_boiler = q_oil / q_available if q_available > 0.0 else 0.0
    closure_error = q_gas - q_oil
    closure_ratio = closure_error / max(abs(q_gas), abs(q_oil), 1.0)
    min_delta_t = min(exhaust_in_k - oil_out_k, exhaust_out_k - oil_in_k)
    minimum_required_delta_t = request.constraints.min_pinch_delta_t_k or 0.0
    approach_issues = validate_minimum_temperature_approach(
        min_delta_t,
        minimum_delta_t_k=minimum_required_delta_t,
        source="boiler",
    )
    if approach_issues:
        first = approach_issues[0]
        return _blocked(
            first.code,
            first.message,
            request,
            source=first.source,
            suggested_action=(
                "Relax the requested boiler duty, increase the allowed stack outlet temperature, or adjust the oil target so the exchanger minimum approach stays positive."
            ),
        )

    result = _base_boiler_result(request)
    _add_boiler_metrics(result, q_available, q_gas, q_oil, eta_boiler, closure_error, closure_ratio, min_delta_t)
    result.solved_streams["resolved_exhaust_stream"] = replace(
        request.exhaust_stream,
        outlet=StatePoint(tag=f"{request.exhaust_stream.inlet.tag}_out", temp_k=exhaust_out_k, pressure_pa=request.exhaust_stream.inlet.pressure_pa),
    )
    result.solved_streams["resolved_oil_stream"] = replace(
        request.oil_stream,
        outlet=StatePoint(tag=f"{request.oil_stream.inlet.tag}_out", temp_k=oil_out_k, pressure_pa=request.oil_stream.inlet.pressure_pa),
    )
    result.metadata.update(
        {
            "calculation_mode": request.mode,
            "design_driver": driver,
            "design_target_value": target,
            "resolved_design_basis": design_basis,
        }
    )
    result.assumptions.extend(
        [
            AssumptionRecord(
                code="ASM-BOILER-002",
                message="Design mode solves a single governing target chosen by the user.",
                source="waste_heat_boiler",
            ),
            AssumptionRecord(
                code="ASM-BOILER-003",
                message=design_basis,
                source="waste_heat_boiler",
            ),
        ]
    )
    result.calc_trace.append(
        CalcTraceEntry(
            step="design_balance",
            message="Solved boiler design target and predicted exhaust and oil outlet temperatures.",
            value_snapshot={
                "driver": str(driver),
                "target_value_si": target,
                "q_available_w": q_available,
                "q_target_w": q_target,
                "oil_out_k": oil_out_k,
                "exhaust_out_k": exhaust_out_k,
                "closure_ratio": closure_ratio,
            },
        )
    )
    _maybe_add_closure_warning(result, request, closure_ratio)
    return result


def _base_boiler_result(request: WasteHeatBoilerRequest) -> ResultEnvelope:
    return ResultEnvelope(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        status=ResultStatus.SUCCESS,
        metadata={"calculation_mode": request.mode},
    )


def _add_boiler_metrics(
    result: ResultEnvelope,
    q_available: float,
    q_gas: float,
    q_oil: float,
    eta_boiler: float,
    closure_error: float,
    closure_ratio: float,
    min_delta_t: float,
) -> None:
    result.add_metric(MetricValue("q_exhaust_available_w", "Available Exhaust Heat", q_available, "W"))
    result.add_metric(MetricValue("q_boiler_transferred_w", "Transferred Boiler Heat", q_gas, "W"))
    result.add_metric(MetricValue("q_oil_absorbed_w", "Oil Absorbed Heat", q_oil, "W"))
    result.add_metric(MetricValue("eta_boiler", "Boiler Efficiency", eta_boiler, "1"))
    result.add_metric(MetricValue("closure_error_w", "Closure Error", closure_error, "W"))
    result.add_metric(MetricValue("closure_ratio", "Closure Ratio", closure_ratio, "1"))
    result.add_metric(MetricValue("min_delta_t_k", "Minimum Temperature Approach", min_delta_t, "K"))


def _maybe_add_closure_warning(result: ResultEnvelope, request: WasteHeatBoilerRequest, closure_ratio: float) -> None:
    if abs(closure_ratio) > request.constraints.max_closure_fraction:
        result.status = ResultStatus.WARNING
        result.warnings.append(
            WarningRecord(
                code="VAL-BOILER-002",
                message="Energy balance closure exceeds the configured tolerance.",
                severity=WarningSeverity.HARD_WARNING,
                source="waste_heat_boiler",
            )
        )


def _blocked(
    code: str,
    reason: str,
    request: WasteHeatBoilerRequest,
    *,
    source: str = "boiler",
    suggested_action: str | None = None,
) -> ResultEnvelope:
    return ResultEnvelope.blocked_result(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        code=code,
        reason=reason,
        source=source,
        suggested_action=suggested_action,
        metadata={"calculation_mode": request.mode},
    )
