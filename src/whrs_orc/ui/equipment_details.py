from __future__ import annotations

from dataclasses import dataclass

from whrs_orc.domain.result_schema import ResultEnvelope
from whrs_orc.solvers.screening_case import ScreeningCaseResult, k_to_c


@dataclass(frozen=True, slots=True)
class EquipmentDetail:
    key: str
    title: str
    status: str
    summary: str
    lines: tuple[str, ...]


def build_idle_equipment_details() -> dict[str, EquipmentDetail]:
    detail = EquipmentDetail(
        key="boiler",
        title="Boiler",
        status="idle",
        summary="Solve a case and click an equipment block to inspect details.",
        lines=(
            "Detail panel remains process-focused.",
            "This area will show temperatures, duty, status, warnings, and assumptions.",
        ),
    )
    return {
        "factory": EquipmentDetail("factory", "Factory", "idle", "Awaiting solve.", ("Exhaust source details will appear here.",)),
        "boiler": detail,
        "oil_pump": EquipmentDetail("oil_pump", "Oil Pump", "idle", "Awaiting solve.", ("Thermal-oil loop details will appear here.",)),
        "heat_exchanger": EquipmentDetail("heat_exchanger", "ORC Heater", "idle", "Awaiting solve.", ("ORC heat uptake details will appear here.",)),
        "turbine": EquipmentDetail("turbine", "Turbine", "idle", "Awaiting solve.", ("Working-fluid heating summary will appear here.",)),
        "generator": EquipmentDetail("generator", "Generator", "idle", "Awaiting solve.", ("Gross power details will appear here.",)),
        "regenerator": EquipmentDetail("regenerator", "Regenerator", "idle", "Awaiting solve.", ("Future detailed ORC layer placeholder.",)),
        "condenser": EquipmentDetail("condenser", "Air Condenser", "idle", "Awaiting solve.", ("Condenser summary will appear here.",)),
        "organic_pump": EquipmentDetail("organic_pump", "Organic Pump", "idle", "Awaiting solve.", ("Power-block basis details will appear here.",)),
    }


def build_equipment_details(result: ScreeningCaseResult | None) -> dict[str, EquipmentDetail]:
    if result is None:
        return build_idle_equipment_details()

    return {
        "factory": _factory_detail(result.boiler_result),
        "boiler": _boiler_detail(result.boiler_result),
        "oil_pump": _oil_loop_detail(result.loop_result),
        "heat_exchanger": _orc_heat_detail(result.orc_heat_result),
        "turbine": _turbine_detail(result.orc_heat_result),
        "generator": _generator_detail(result.orc_power_result),
        "regenerator": _regenerator_detail(result.orc_heat_result),
        "condenser": _condenser_detail(result.orc_power_result),
        "organic_pump": _organic_pump_detail(result.orc_power_result),
    }


def render_equipment_detail(detail: EquipmentDetail) -> str:
    lines = [f"Status: {detail.status}", detail.summary]
    lines.extend(detail.lines)
    return "\n".join(lines)


def _factory_detail(envelope: ResultEnvelope) -> EquipmentDetail:
    if envelope.blocked_state.blocked:
        return _blocked_detail("factory", "Factory", envelope)
    stream = envelope.solved_streams.get("resolved_exhaust_stream")
    stream_line = "Temperatures pending"
    if stream is not None and stream.outlet is not None and stream.outlet.temp_k is not None:
        stream_line = f"Exhaust T: {k_to_c(stream.inlet.temp_k):.1f} -> {k_to_c(stream.outlet.temp_k):.1f} C"
    return EquipmentDetail(
        key="factory",
        title="Factory / Exhaust Source",
        status=str(envelope.status),
        summary=_metric_line(envelope, "q_exhaust_available_w", "Available exhaust heat"),
        lines=(
            stream_line,
            _warning_line(envelope),
        ),
    )


def _boiler_detail(envelope: ResultEnvelope) -> EquipmentDetail:
    if envelope.blocked_state.blocked:
        return _blocked_detail("boiler", "Boiler", envelope)
    return EquipmentDetail(
        key="boiler",
        title="Waste Heat Boiler",
        status=str(envelope.status),
        summary=_metric_line(envelope, "q_boiler_transferred_w", "Transferred heat"),
        lines=(
            _metric_line(envelope, "eta_boiler", "Boiler efficiency"),
            _metric_line(envelope, "min_delta_t_k", "Minimum temperature approach"),
            _metric_line(envelope, "closure_ratio", "Closure ratio"),
            _warning_line(envelope),
        ),
    )


def _oil_loop_detail(envelope: ResultEnvelope | None) -> EquipmentDetail:
    if envelope is None:
        return build_idle_equipment_details()["oil_pump"]
    if envelope.blocked_state.blocked:
        return _blocked_detail("oil_pump", "Oil Pump / Loop", envelope)
    return EquipmentDetail(
        key="oil_pump",
        title="Thermal Oil Loop",
        status=str(envelope.status),
        summary=_metric_line(envelope, "q_loop_loss_w", "Loop heat loss"),
        lines=(
            _metric_line(envelope, "estimated_pump_power_w", "Estimated pump power"),
            _warning_line(envelope),
        ),
    )


def _orc_heat_detail(envelope: ResultEnvelope | None) -> EquipmentDetail:
    if envelope is None:
        return build_idle_equipment_details()["heat_exchanger"]
    if envelope.blocked_state.blocked:
        return _blocked_detail("heat_exchanger", "ORC Heater", envelope)
    return EquipmentDetail(
        key="heat_exchanger",
        title="ORC Heater",
        status=str(envelope.status),
        summary=_metric_line(envelope, "q_orc_absorbed_w", "ORC absorbed heat"),
        lines=(
            _metric_line(envelope, "min_approach_k", "Minimum approach"),
            _metric_line(envelope, "wf_temp_gain_k", "WF temperature gain"),
            _warning_line(envelope),
        ),
    )


def _turbine_detail(envelope: ResultEnvelope | None) -> EquipmentDetail:
    if envelope is None:
        return build_idle_equipment_details()["turbine"]
    if envelope.blocked_state.blocked:
        return _blocked_detail("turbine", "Turbine", envelope)
    mode = str(envelope.metadata.get("calculation_mode", "")).replace("_", " ")
    return EquipmentDetail(
        key="turbine",
        title="Turbine Inlet Screening",
        status=str(envelope.status),
        summary=_metric_line(envelope, "wf_temp_gain_k", "Working-fluid heating"),
        lines=(
            f"Mode: {mode or '-'}",
            _metric_line(envelope, "q_orc_absorbed_w", "Heat basis"),
            _warning_line(envelope),
        ),
    )


def _generator_detail(envelope: ResultEnvelope | None) -> EquipmentDetail:
    if envelope is None:
        return build_idle_equipment_details()["generator"]
    if envelope.blocked_state.blocked:
        return _blocked_detail("generator", "Generator", envelope)
    return EquipmentDetail(
        key="generator",
        title="Generator",
        status=str(envelope.status),
        summary=_metric_line(envelope, "gross_electric_power_w", "Gross electric power"),
        lines=(
            _metric_line(envelope, "eta_orc_gross", "Gross ORC efficiency"),
            _metric_line(envelope, "eta_system_gross", "Gross system efficiency"),
            _warning_line(envelope),
        ),
    )


def _regenerator_detail(envelope: ResultEnvelope | None) -> EquipmentDetail:
    if envelope is None:
        return build_idle_equipment_details()["regenerator"]
    mode = str(envelope.metadata.get("calculation_mode", "")).replace("_", " ")
    return EquipmentDetail(
        key="regenerator",
        title="Regenerator",
        status=str(envelope.status),
        summary="Detailed ORC recuperation is still a future layer.",
        lines=(
            f"Current screening basis: {mode or '-'}",
            "The present release does not solve a dedicated regenerator energy balance.",
        ),
    )


def _condenser_detail(envelope: ResultEnvelope | None) -> EquipmentDetail:
    if envelope is None:
        return build_idle_equipment_details()["condenser"]
    if envelope.blocked_state.blocked:
        return _blocked_detail("condenser", "Air Condenser", envelope)
    return EquipmentDetail(
        key="condenser",
        title="Air Condenser",
        status=str(envelope.status),
        summary=_metric_line(envelope, "eta_system_gross", "Gross system efficiency"),
        lines=(
            _metric_line(envelope, "gross_electric_power_w", "Power basis"),
            _warning_line(envelope),
        ),
    )


def _organic_pump_detail(envelope: ResultEnvelope | None) -> EquipmentDetail:
    if envelope is None:
        return build_idle_equipment_details()["organic_pump"]
    if envelope.blocked_state.blocked:
        return _blocked_detail("organic_pump", "Organic Pump", envelope)
    mode = str(envelope.metadata.get("calculation_mode", "")).replace("_", " ")
    return EquipmentDetail(
        key="organic_pump",
        title="Organic Pump / Power Basis",
        status=str(envelope.status),
        summary=f"Power mode: {mode or '-'}",
        lines=(
            _metric_line(envelope, "eta_orc_gross", "Gross efficiency basis"),
            _metric_line(envelope, "gross_electric_power_w", "Gross electric power"),
        ),
    )


def _blocked_detail(key: str, title: str, envelope: ResultEnvelope) -> EquipmentDetail:
    lines = [envelope.blocked_state.reason or "Blocked."]
    if envelope.blocked_state.suggested_action:
        lines.append(f"Suggested action: {envelope.blocked_state.suggested_action}")
    return EquipmentDetail(
        key=key,
        title=title,
        status="blocked",
        summary="This stage is currently blocked.",
        lines=tuple(lines),
    )


def _metric_line(envelope: ResultEnvelope, key: str, label: str) -> str:
    metric = envelope.values.get(key)
    if metric is None:
        return f"{label}: --"
    value = metric.value_si
    if key.endswith("_w"):
        return f"{label}: {value / 1000.0:,.1f} kW"
    if key.endswith("_k"):
        return f"{label}: {value:,.2f} K"
    if key.startswith("eta_") or key.endswith("_ratio"):
        return f"{label}: {100.0 * value:,.2f} %"
    return f"{label}: {value:,.4g}"


def _warning_line(envelope: ResultEnvelope) -> str:
    if not envelope.warnings:
        return "Warnings: none"
    first = envelope.warnings[0]
    return f"Warning: {first.code} - {first.message}"
