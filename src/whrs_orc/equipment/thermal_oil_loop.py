from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from whrs_orc.domain.models import FluidKind, StatePoint
from whrs_orc.domain.result_schema import AssumptionRecord, CalcTraceEntry, MetricValue, ResultEnvelope, ResultStatus
from whrs_orc.equipment.contracts import ThermalOilLoopMode, ThermalOilLoopRequest
from whrs_orc.properties.thermal_oil_properties import ThermalOilPropertyProvider
from whrs_orc.solvers.validation_rules import ValidationAction, validate_positive_mass_flow, validate_state_temperature


MODEL_NAME = "thermal_oil_loop"
MODEL_VERSION = "0.1.0"


def solve_thermal_oil_loop(
    request: ThermalOilLoopRequest,
    *,
    oil_provider: ThermalOilPropertyProvider | None = None,
) -> ResultEnvelope:
    oil_provider = oil_provider or ThermalOilPropertyProvider()

    if request.oil_supply_stream.fluid.kind is not FluidKind.THERMAL_OIL:
        return _blocked("VAL-KIND-OIL", "Thermal-oil loop requires a thermal-oil supply stream.", request)
    if request.oil_return_stream.fluid.kind is not FluidKind.THERMAL_OIL:
        return _blocked("VAL-KIND-OIL", "Thermal-oil loop requires a thermal-oil return stream.", request)

    issues = []
    issues.extend(validate_positive_mass_flow(request.oil_supply_stream))
    issues.extend(validate_positive_mass_flow(request.oil_return_stream))
    issues.extend(validate_state_temperature(request.oil_supply_stream.inlet.temp_k, source="oil_supply_inlet"))
    blocking = [issue for issue in issues if issue.action is ValidationAction.BLOCK]
    if blocking:
        first = blocking[0]
        return _blocked(first.code, first.message, request, source=first.source)

    supply_inlet_k = request.oil_supply_stream.inlet.temp_k
    assert supply_inlet_k is not None

    if request.mode is ThermalOilLoopMode.ADIABATIC_LINK:
        delivered_outlet_k = supply_inlet_k
        q_loss_w = 0.0
    elif request.mode is ThermalOilLoopMode.RATED_HEAT_LOSS:
        if "line_heat_loss_w" in request.parameters:
            q_loss_w = float(request.parameters["line_heat_loss_w"])
        elif "line_heat_loss_fraction" in request.parameters:
            q_loss_w = max(float(request.parameters["line_heat_loss_fraction"]), 0.0) * request.oil_supply_stream.mass_flow_kg_s * oil_provider.cp_j_kg_k(request.oil_supply_stream.fluid, supply_inlet_k).value
        else:
            return _blocked("VAL-LOOP-001", "Rated heat-loss mode requires `line_heat_loss_w` or `line_heat_loss_fraction`.", request)
        if q_loss_w < 0.0:
            return _blocked("VAL-LOOP-002", "Line heat loss cannot be negative.", request)
        specific_loss = q_loss_w / request.oil_supply_stream.mass_flow_kg_s
        delivered_outlet_k, achieved_specific_loss = oil_provider.solve_outlet_temp_k(
            request.oil_supply_stream.fluid,
            supply_inlet_k,
            -specific_loss,
        ) if specific_loss < 0.0 else _solve_cooling_outlet(
            oil_provider,
            request.oil_supply_stream.fluid,
            supply_inlet_k,
            specific_loss,
        )
        q_loss_w = achieved_specific_loss * request.oil_supply_stream.mass_flow_kg_s
    elif request.mode is ThermalOilLoopMode.TARGET_DELIVERY_TEMPERATURE:
        target_delivery_k = request.parameters.get("target_delivery_temp_k")
        if target_delivery_k is None:
            return _blocked("VAL-LOOP-003", "Target delivery temperature mode requires `target_delivery_temp_k`.", request)
        delivered_outlet_k = float(target_delivery_k)
        if delivered_outlet_k > supply_inlet_k:
            return _blocked("VAL-LOOP-004", "Target delivery temperature cannot exceed oil supply temperature.", request)
        specific_loss = oil_provider.heat_gain_j_kg(request.oil_supply_stream.fluid, delivered_outlet_k, supply_inlet_k).value
        q_loss_w = specific_loss * request.oil_supply_stream.mass_flow_kg_s
    else:
        return _blocked("VAL-MODE-001", f"Unsupported thermal-oil loop mode `{request.mode}`.", request)

    if delivered_outlet_k <= 0.0:
        return _blocked("VAL-LOOP-005", "Delivered oil temperature became non-physical.", request)

    limits = request.oil_supply_stream.fluid.limits or oil_provider.limits(request.oil_supply_stream.fluid)
    max_bulk_k = request.constraints.max_oil_bulk_temp_k or (limits.max_bulk_temp_k if limits is not None else None)
    if max_bulk_k is not None and delivered_outlet_k > max_bulk_k:
        return _blocked("VAL-OIL-001", "Delivered oil temperature exceeds the allowed oil bulk temperature limit.", request)

    delivered_stream = replace(
        request.oil_supply_stream,
        outlet=StatePoint(tag=f"{request.oil_supply_stream.inlet.tag}_delivered", temp_k=delivered_outlet_k, pressure_pa=request.oil_supply_stream.inlet.pressure_pa),
    )

    result = ResultEnvelope(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        status=ResultStatus.SUCCESS,
        metadata={"calculation_mode": request.mode},
    )
    result.add_metric(MetricValue("q_loop_loss_w", "Loop Heat Loss", q_loss_w, "W"))
    result.add_metric(MetricValue("delta_t_loop_k", "Loop Temperature Drop", supply_inlet_k - delivered_outlet_k, "K"))

    line_pressure_drop_pa = float(request.parameters.get("line_pressure_drop_pa", 0.0))
    pump_efficiency = float(request.parameters.get("pump_efficiency", 1.0))
    estimated_pump_power_w = 0.0
    density = oil_provider.density_kg_m3(request.oil_supply_stream.fluid)
    if line_pressure_drop_pa > 0.0 and density and pump_efficiency > 0.0:
        volumetric_flow_m3_s = request.oil_supply_stream.mass_flow_kg_s / density
        estimated_pump_power_w = line_pressure_drop_pa * volumetric_flow_m3_s / pump_efficiency
    result.add_metric(MetricValue("estimated_pump_power_w", "Estimated Pump Power", estimated_pump_power_w, "W"))

    result.solved_streams["oil_delivered_stream"] = delivered_stream
    result.solved_streams["oil_return_resolved_stream"] = request.oil_return_stream
    result.assumptions.append(
        AssumptionRecord(
            code="ASM-LOOP-001",
            message="Thermal-oil loop is modeled as a screening transport block with lumped heat loss.",
            source="thermal_oil_loop",
        )
    )
    result.calc_trace.append(
        CalcTraceEntry(
            step="loop_transport",
            message="Calculated delivered oil condition and loop heat loss.",
            value_snapshot={
                "supply_temp_k": supply_inlet_k,
                "delivered_temp_k": delivered_outlet_k,
                "q_loop_loss_w": q_loss_w,
                "estimated_pump_power_w": estimated_pump_power_w,
            },
        )
    )
    return result


def _solve_cooling_outlet(
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


def _blocked(code: str, reason: str, request: ThermalOilLoopRequest, *, source: str = "thermal_oil_loop") -> ResultEnvelope:
    return ResultEnvelope.blocked_result(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        code=code,
        reason=reason,
        source=source,
        metadata={"calculation_mode": request.mode},
    )

