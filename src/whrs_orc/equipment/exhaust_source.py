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
)
from whrs_orc.equipment.contracts import ExhaustSourceMode, ExhaustSourceRequest
from whrs_orc.properties.exhaust_properties import ExhaustPropertyProvider
from whrs_orc.solvers.validation_rules import (
    ValidationAction,
    validate_composition_sum,
    validate_positive_mass_flow,
    validate_pressure,
    validate_state_temperature,
)


MODEL_NAME = "exhaust_source"
MODEL_VERSION = "0.1.0"


def solve_exhaust_source(
    request: ExhaustSourceRequest,
    *,
    property_provider: ExhaustPropertyProvider | None = None,
) -> ResultEnvelope:
    property_provider = property_provider or ExhaustPropertyProvider()
    issues = []
    issues.extend(validate_positive_mass_flow(request.exhaust_stream))
    issues.extend(validate_state_temperature(request.exhaust_stream.inlet.temp_k, source="exhaust_inlet"))
    issues.extend(validate_pressure(request.exhaust_stream.inlet.pressure_pa, source="exhaust_inlet"))
    issues.extend(validate_composition_sum(request.exhaust_stream))

    if request.exhaust_stream.fluid.kind is not FluidKind.EXHAUST_GAS:
        return _blocked("VAL-KIND-EXH", "Exhaust source requires an exhaust-gas stream.", request)

    blocking = [issue for issue in issues if issue.action is ValidationAction.BLOCK]
    if blocking:
        first = blocking[0]
        return _blocked(first.code, first.message, request, source=first.source)

    inlet_temp_k = request.exhaust_stream.inlet.temp_k
    assert inlet_temp_k is not None
    inlet_pressure_pa = request.exhaust_stream.inlet.pressure_pa

    if request.mode is ExhaustSourceMode.AVAILABLE_HEAT_FROM_STACK_LIMIT:
        stack_min_k = request.constraints.stack_min_temp_k
        if stack_min_k is None:
            return _blocked("VAL-STACK-REQ", "Stack minimum temperature is required for available-heat mode.", request)
        if inlet_temp_k <= stack_min_k:
            return _blocked("VAL-STACK-001", "Exhaust inlet temperature must be above the selected stack minimum temperature.", request)
        specific_heat_release = property_provider.heat_release_j_kg(
            request.exhaust_stream.fluid,
            inlet_temp_k,
            stack_min_k,
            inlet_pressure_pa,
        )
        outlet_state = StatePoint(
            tag=f"{request.exhaust_stream.inlet.tag}_stack",
            temp_k=stack_min_k,
            pressure_pa=inlet_pressure_pa,
        )
        metric_key = "available_heat_w"
        display_name = "Available Heat"
        total_heat_w = request.exhaust_stream.mass_flow_kg_s * specific_heat_release.value
    elif request.mode is ExhaustSourceMode.RELEASED_HEAT_FROM_OUTLET_TEMPERATURE:
        if request.exhaust_stream.outlet is None or request.exhaust_stream.outlet.temp_k is None:
            return _blocked("VAL-OUTLET-REQ", "Exhaust outlet temperature is required for released-heat mode.", request)
        outlet_state = request.exhaust_stream.outlet
        if inlet_temp_k <= outlet_state.temp_k:
            return _blocked("VAL-HX-001", "Exhaust inlet temperature must be greater than exhaust outlet temperature.", request)
        specific_heat_release = property_provider.heat_release_j_kg(
            request.exhaust_stream.fluid,
            inlet_temp_k,
            outlet_state.temp_k,
            inlet_pressure_pa,
        )
        metric_key = "released_heat_w"
        display_name = "Released Heat"
        total_heat_w = request.exhaust_stream.mass_flow_kg_s * specific_heat_release.value
    else:
        return _blocked("VAL-MODE-001", f"Unsupported exhaust source mode `{request.mode}`.", request)

    cp_mid = property_provider.cp_j_kg_k(request.exhaust_stream.fluid, 0.5 * (inlet_temp_k + (outlet_state.temp_k or inlet_temp_k)), inlet_pressure_pa)
    result = ResultEnvelope(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        status=ResultStatus.SUCCESS,
        metadata={"calculation_mode": request.mode, "property_backends": {"exhaust": cp_mid.source}},
    )
    result.add_metric(MetricValue(metric_key, display_name, total_heat_w, "W", source=specific_heat_release.source))
    result.add_metric(MetricValue("cp_mix_avg_j_kg_k", "Average Exhaust Cp", cp_mid.value, "J/kg/K", source=cp_mid.source))
    result.solved_streams["resolved_exhaust_stream"] = replace(request.exhaust_stream, outlet=outlet_state)
    result.assumptions.append(
        AssumptionRecord(
            code="ASM-EXH-001",
            message="Exhaust heat release is obtained by integrating the resolved mixture heat capacity.",
            source="exhaust_source",
        )
    )
    result.calc_trace.append(
        CalcTraceEntry(
            step="heat_release",
            message="Calculated exhaust-side heat release from inlet and resolved outlet temperatures.",
            value_snapshot={
                "inlet_temp_k": inlet_temp_k,
                "outlet_temp_k": outlet_state.temp_k or 0.0,
                "specific_heat_release_j_kg": specific_heat_release.value,
                "total_heat_w": total_heat_w,
            },
            backend_used=specific_heat_release.source,
        )
    )
    return result


def _blocked(
    code: str,
    reason: str,
    request: ExhaustSourceRequest,
    *,
    source: str = "exhaust_source",
) -> ResultEnvelope:
    return ResultEnvelope.blocked_result(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        code=code,
        reason=reason,
        source=source,
        metadata={"calculation_mode": request.mode},
    )
