from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from whrs_orc.domain.models import FluidKind, StatePoint
from whrs_orc.domain.result_schema import AssumptionRecord, CalcTraceEntry, MetricValue, ResultEnvelope, ResultStatus
from whrs_orc.equipment.contracts import OrcScreeningHeatMode, OrcScreeningHeatRequest
from whrs_orc.properties.thermal_oil_properties import ThermalOilPropertyProvider
from whrs_orc.properties.working_fluid_screening import WorkingFluidScreeningProvider
from whrs_orc.solvers.validation_rules import ValidationAction, validate_positive_mass_flow, validate_state_temperature


MODEL_NAME = "orc_screening_heat_uptake"
MODEL_VERSION = "0.1.0"


def solve_orc_screening_heat_uptake(
    request: OrcScreeningHeatRequest,
    *,
    oil_provider: ThermalOilPropertyProvider | None = None,
    wf_provider: WorkingFluidScreeningProvider | None = None,
) -> ResultEnvelope:
    oil_provider = oil_provider or ThermalOilPropertyProvider()
    wf_provider = wf_provider or WorkingFluidScreeningProvider()

    if request.oil_hot_stream.fluid.kind is not FluidKind.THERMAL_OIL:
        return _blocked("VAL-KIND-OIL", "ORC screening heat uptake requires a thermal-oil hot stream.", request)
    if request.wf_cold_stream.fluid.kind is not FluidKind.WORKING_FLUID:
        return _blocked("VAL-KIND-WF", "ORC screening heat uptake requires a working-fluid cold stream.", request)

    issues = []
    issues.extend(validate_positive_mass_flow(request.oil_hot_stream))
    issues.extend(validate_positive_mass_flow(request.wf_cold_stream))
    issues.extend(validate_state_temperature(request.oil_hot_stream.inlet.temp_k, source="oil_hot_inlet"))
    issues.extend(validate_state_temperature(request.wf_cold_stream.inlet.temp_k, source="wf_inlet"))
    blocking = [issue for issue in issues if issue.action is ValidationAction.BLOCK]
    if blocking:
        first = blocking[0]
        return _blocked(first.code, first.message, request, source=first.source)

    oil_in_k = request.oil_hot_stream.inlet.temp_k
    wf_in_k = request.wf_cold_stream.inlet.temp_k
    assert oil_in_k is not None and wf_in_k is not None

    if request.mode is OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE:
        if request.oil_hot_stream.outlet is None or request.oil_hot_stream.outlet.temp_k is None:
            return _blocked("VAL-ORC-005", "Oil outlet temperature is required for oil-side screening mode.", request)
        oil_out_k = request.oil_hot_stream.outlet.temp_k
        if oil_out_k >= oil_in_k:
            return _blocked("VAL-HX-001", "Oil outlet temperature must be below oil inlet temperature in screening mode.", request)
        q_orc_absorbed_w = request.oil_hot_stream.mass_flow_kg_s * oil_provider.heat_gain_j_kg(
            request.oil_hot_stream.fluid,
            oil_out_k,
            oil_in_k,
        ).value
        wf_out_k, achieved_q_per_kg = wf_provider.solve_outlet_temp_k(
            request.wf_cold_stream.fluid,
            wf_in_k,
            q_orc_absorbed_w / request.wf_cold_stream.mass_flow_kg_s,
            pressure_pa=request.wf_cold_stream.inlet.pressure_pa,
            upper_bound_temp_k=request.constraints.max_wf_outlet_temp_k,
        )
        q_orc_absorbed_w = achieved_q_per_kg * request.wf_cold_stream.mass_flow_kg_s
    elif request.mode is OrcScreeningHeatMode.SINGLE_PHASE_TEMPERATURE_GAIN:
        target_wf_out_k = request.parameters.get("target_wf_outlet_temp_k")
        if target_wf_out_k is None:
            return _blocked("VAL-ORC-006", "Single-phase temperature-gain mode requires `target_wf_outlet_temp_k`.", request)
        wf_out_k = float(target_wf_out_k)
        if wf_out_k <= wf_in_k:
            return _blocked("VAL-HX-002", "Working-fluid outlet temperature must be above inlet temperature.", request)
        upper_bound = request.constraints.max_wf_outlet_temp_k
        if upper_bound is not None and wf_out_k > upper_bound:
            return _blocked("VAL-ORC-002", "Requested working-fluid outlet temperature exceeds the supported screening single-phase range.", request)
        q_orc_absorbed_w = request.wf_cold_stream.mass_flow_kg_s * wf_provider.heat_gain_j_kg(
            request.wf_cold_stream.fluid,
            wf_in_k,
            wf_out_k,
            request.wf_cold_stream.inlet.pressure_pa,
        ).value
        if request.oil_hot_stream.outlet is None or request.oil_hot_stream.outlet.temp_k is None:
            oil_out_k, achieved_q_per_kg = _solve_oil_cooling_outlet(
                oil_provider,
                request.oil_hot_stream.fluid,
                oil_in_k,
                q_orc_absorbed_w / request.oil_hot_stream.mass_flow_kg_s,
            )
            q_orc_absorbed_w = achieved_q_per_kg * request.oil_hot_stream.mass_flow_kg_s
        else:
            oil_out_k = request.oil_hot_stream.outlet.temp_k
    elif request.mode is OrcScreeningHeatMode.KNOWN_ORC_HEAT_INPUT:
        q_orc_absorbed_w = float(request.parameters.get("q_orc_absorbed_target_w", 0.0))
        if q_orc_absorbed_w <= 0.0:
            return _blocked("VAL-ORC-007", "Known ORC heat-input mode requires positive `q_orc_absorbed_target_w`.", request)
        wf_out_k, achieved_q_per_kg = wf_provider.solve_outlet_temp_k(
            request.wf_cold_stream.fluid,
            wf_in_k,
            q_orc_absorbed_w / request.wf_cold_stream.mass_flow_kg_s,
            pressure_pa=request.wf_cold_stream.inlet.pressure_pa,
            upper_bound_temp_k=request.constraints.max_wf_outlet_temp_k,
        )
        q_orc_absorbed_w = achieved_q_per_kg * request.wf_cold_stream.mass_flow_kg_s
        oil_out_k, achieved_q_per_kg_oil = _solve_oil_cooling_outlet(
            oil_provider,
            request.oil_hot_stream.fluid,
            oil_in_k,
            q_orc_absorbed_w / request.oil_hot_stream.mass_flow_kg_s,
        )
        q_orc_absorbed_w = achieved_q_per_kg_oil * request.oil_hot_stream.mass_flow_kg_s
    else:
        return _blocked("VAL-MODE-001", f"Unsupported ORC screening heat mode `{request.mode}`.", request)

    if oil_out_k >= oil_in_k:
        return _blocked("VAL-HX-001", "Resolved oil outlet temperature must be below oil inlet temperature.", request)

    min_approach_k = min(oil_in_k - wf_out_k, oil_out_k - wf_in_k)
    if request.constraints.min_approach_delta_t_k is not None and min_approach_k < request.constraints.min_approach_delta_t_k:
        return _blocked("VAL-HX-003", "Resolved ORC screening heat transfer violates the minimum temperature approach.", request)

    result = ResultEnvelope(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        status=ResultStatus.SUCCESS,
        metadata={"calculation_mode": request.mode, "phase_path_supported": True},
    )
    result.add_metric(MetricValue("q_orc_absorbed_w", "ORC Absorbed Heat", q_orc_absorbed_w, "W"))
    result.add_metric(MetricValue("wf_temp_gain_k", "Working-Fluid Temperature Gain", wf_out_k - wf_in_k, "K"))
    result.add_metric(MetricValue("min_approach_k", "Minimum Temperature Approach", min_approach_k, "K"))
    result.solved_streams["resolved_oil_stream"] = replace(
        request.oil_hot_stream,
        outlet=StatePoint(tag=f"{request.oil_hot_stream.inlet.tag}_out", temp_k=oil_out_k, pressure_pa=request.oil_hot_stream.inlet.pressure_pa),
    )
    result.solved_streams["resolved_wf_stream"] = replace(
        request.wf_cold_stream,
        outlet=StatePoint(tag=f"{request.wf_cold_stream.inlet.tag}_out", temp_k=wf_out_k, pressure_pa=request.wf_cold_stream.inlet.pressure_pa),
    )
    result.assumptions.append(
        AssumptionRecord(
            code="ASM-ORC-001",
            message="ORC screening heat uptake is limited to supported single-phase temperature-gain behavior.",
            source="orc_screening_heat_uptake",
        )
    )
    result.calc_trace.append(
        CalcTraceEntry(
            step="orc_screening_heat",
            message="Calculated ORC absorbed heat and working-fluid temperature rise from screening inputs.",
            value_snapshot={
                "q_orc_absorbed_w": q_orc_absorbed_w,
                "oil_in_k": oil_in_k,
                "oil_out_k": oil_out_k,
                "wf_in_k": wf_in_k,
                "wf_out_k": wf_out_k,
                "min_approach_k": min_approach_k,
            },
        )
    )
    return result


def _solve_oil_cooling_outlet(
    oil_provider: ThermalOilPropertyProvider,
    fluid,
    inlet_temp_k: float,
    target_heat_loss_j_kg: float,
    *,
    tolerance_j_kg: float = 1.0,
) -> tuple[float, float]:
    if target_heat_loss_j_kg <= 0.0:
        return inlet_temp_k, 0.0
    lower = max(1.0, inlet_temp_k - 400.0)
    upper = inlet_temp_k
    achievable = oil_provider.heat_gain_j_kg(fluid, lower, inlet_temp_k).value
    if achievable <= target_heat_loss_j_kg:
        return lower, achievable
    for _ in range(80):
        mid = 0.5 * (lower + upper)
        heat_mid = oil_provider.heat_gain_j_kg(fluid, mid, inlet_temp_k).value
        if abs(heat_mid - target_heat_loss_j_kg) <= tolerance_j_kg:
            return mid, heat_mid
        if heat_mid > target_heat_loss_j_kg:
            lower = mid
        else:
            upper = mid
    mid = 0.5 * (lower + upper)
    return mid, oil_provider.heat_gain_j_kg(fluid, mid, inlet_temp_k).value


def _blocked(code: str, reason: str, request: OrcScreeningHeatRequest, *, source: str = "orc_screening_heat_uptake") -> ResultEnvelope:
    return ResultEnvelope.blocked_result(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        code=code,
        reason=reason,
        source=source,
        metadata={"calculation_mode": request.mode},
    )

