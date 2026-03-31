from __future__ import annotations

from dataclasses import dataclass

from whrs_orc.domain.models import ProcessStream
from whrs_orc.domain.result_schema import ResultEnvelope, ResultStatus
from whrs_orc.solvers.screening_case import ScreeningCaseResult, k_to_c


@dataclass(frozen=True, slots=True)
class DiagramStage:
    title: str
    primary_text: str
    secondary_text: str
    status: str


@dataclass(frozen=True, slots=True)
class ProcessDiagramSnapshot:
    headline: str
    factory: DiagramStage
    boiler: DiagramStage
    oil_pump: DiagramStage
    heat_exchanger: DiagramStage
    turbine: DiagramStage
    generator: DiagramStage
    regenerator: DiagramStage
    condenser: DiagramStage
    organic_pump: DiagramStage


def build_empty_process_snapshot() -> ProcessDiagramSnapshot:
    idle = DiagramStage("Idle", "Awaiting solve", "", "idle")
    return ProcessDiagramSnapshot(
        headline="Solve a case to populate the process view.",
        factory=DiagramStage("Factory", "Exhaust source", "Awaiting solve", "idle"),
        boiler=DiagramStage("Boiler", "Transferred heat", "Awaiting solve", "idle"),
        oil_pump=DiagramStage("Oil Pump", "Loop transport", "Awaiting solve", "idle"),
        heat_exchanger=DiagramStage("ORC Heater", "ORC absorbed heat", "Awaiting solve", "idle"),
        turbine=DiagramStage("Turbine", "WF temperature gain", "Awaiting solve", "idle"),
        generator=DiagramStage("Generator", "Gross electric power", "Awaiting solve", "idle"),
        regenerator=DiagramStage("Regenerator", "Next phase", "Detailed ORC model later", "idle"),
        condenser=DiagramStage("Air Condenser", "System efficiency", "Awaiting solve", "idle"),
        organic_pump=DiagramStage("Organic Pump", "Power basis", "Awaiting solve", "idle"),
    )


def build_process_snapshot(result: ScreeningCaseResult | None) -> ProcessDiagramSnapshot:
    if result is None:
        return build_empty_process_snapshot()

    boiler = result.boiler_result
    loop = result.loop_result
    orc_heat = result.orc_heat_result
    orc_power = result.orc_power_result

    headline = _build_headline(boiler, loop, orc_heat, orc_power)

    return ProcessDiagramSnapshot(
        headline=headline,
        factory=_build_factory_stage(boiler),
        boiler=_build_boiler_stage(boiler),
        oil_pump=_build_oil_pump_stage(loop),
        heat_exchanger=_build_heat_exchanger_stage(orc_heat),
        turbine=_build_turbine_stage(orc_heat),
        generator=_build_generator_stage(orc_power),
        regenerator=_build_regenerator_stage(orc_heat),
        condenser=_build_condenser_stage(orc_power),
        organic_pump=_build_organic_pump_stage(orc_power),
    )


def status_color(status: str) -> str:
    palette = {
        "success": "#2e8b57",
        "warning": "#d08a00",
        "blocked": "#c0392b",
        "error": "#8e2b5b",
        "idle": "#8d99a6",
    }
    return palette.get(status, palette["idle"])


def _build_headline(
    boiler: ResultEnvelope | None,
    loop: ResultEnvelope | None,
    orc_heat: ResultEnvelope | None,
    orc_power: ResultEnvelope | None,
) -> str:
    for envelope in [boiler, loop, orc_heat, orc_power]:
        if envelope is not None and envelope.blocked_state.blocked:
            return f"Blocked at {envelope.model_name}: {envelope.blocked_state.reason}"
    if orc_power is not None and orc_power.status in {ResultStatus.SUCCESS, ResultStatus.WARNING}:
        gross_power = orc_power.values.get("gross_electric_power_w")
        if gross_power is not None:
            return f"Gross electric output: {_format_power(gross_power.value_si)}"
    return "Screening chain solved."


def _build_factory_stage(boiler: ResultEnvelope) -> DiagramStage:
    if boiler.blocked_state.blocked:
        return _blocked_stage("Factory", boiler)
    exhaust_stream = boiler.solved_streams.get("resolved_exhaust_stream")
    q_available = _metric_text(boiler, "q_exhaust_available_w", _format_power)
    temp_text = _stream_temp_pair(exhaust_stream) if exhaust_stream is not None else "Temperatures pending"
    return DiagramStage("Factory", f"Qavail {q_available}", temp_text, _stage_status(boiler))


def _build_boiler_stage(boiler: ResultEnvelope) -> DiagramStage:
    if boiler.blocked_state.blocked:
        return _blocked_stage("Boiler", boiler)
    q_text = _metric_text(boiler, "q_boiler_transferred_w", _format_power)
    eta_text = _metric_text(boiler, "eta_boiler", _format_percent)
    return DiagramStage("Boiler", f"Q {q_text}", f"eta {eta_text}", _stage_status(boiler))


def _build_oil_pump_stage(loop: ResultEnvelope | None) -> DiagramStage:
    if loop is None:
        return DiagramStage("Oil Pump", "Waiting for loop solve", "", "idle")
    if loop.blocked_state.blocked:
        return _blocked_stage("Oil Pump", loop)
    loss_text = _metric_text(loop, "q_loop_loss_w", _format_power)
    pump_text = _metric_text(loop, "estimated_pump_power_w", _format_power)
    return DiagramStage("Oil Pump", f"Loss {loss_text}", f"Pump {pump_text}", _stage_status(loop))


def _build_heat_exchanger_stage(orc_heat: ResultEnvelope | None) -> DiagramStage:
    if orc_heat is None:
        return DiagramStage("ORC Heater", "Waiting for ORC heat solve", "", "idle")
    if orc_heat.blocked_state.blocked:
        return _blocked_stage("ORC Heater", orc_heat)
    heat_text = _metric_text(orc_heat, "q_orc_absorbed_w", _format_power)
    approach_text = _metric_text(orc_heat, "min_approach_k", _format_kelvin)
    stage_count = int(orc_heat.metadata.get("heater_stage_count", 1) or 1)
    return DiagramStage("ORC Heater", f"{stage_count} stage | Qorc {heat_text}", f"dTmin {approach_text}", _stage_status(orc_heat))


def _build_turbine_stage(orc_heat: ResultEnvelope | None) -> DiagramStage:
    if orc_heat is None:
        return DiagramStage("Turbine", "WF gain pending", "", "idle")
    if orc_heat.blocked_state.blocked:
        return _blocked_stage("Turbine", orc_heat)
    gain_text = _metric_text(orc_heat, "wf_temp_gain_k", _format_kelvin)
    heat_mode = str(orc_heat.metadata.get("calculation_mode", "")).replace("_", " ")
    return DiagramStage("Turbine", f"WF gain {gain_text}", _shorten(heat_mode, 24), _stage_status(orc_heat))


def _build_generator_stage(orc_power: ResultEnvelope | None) -> DiagramStage:
    if orc_power is None:
        return DiagramStage("Generator", "Gross power pending", "", "idle")
    if orc_power.blocked_state.blocked:
        return _blocked_stage("Generator", orc_power)
    power_text = _metric_text(orc_power, "gross_electric_power_w", _format_power)
    eff_text = _metric_text(orc_power, "eta_orc_gross", _format_percent)
    return DiagramStage("Generator", f"Pgross {power_text}", f"eta {eff_text}", _stage_status(orc_power))


def _build_regenerator_stage(orc_heat: ResultEnvelope | None) -> DiagramStage:
    if orc_heat is None:
        return DiagramStage("Regenerator", "Planned layer", "Detailed model later", "idle")
    return DiagramStage(
        "Regenerator",
        "Screening backbone",
        _shorten(str(orc_heat.metadata.get("calculation_mode", "")).replace("_", " "), 24),
        _stage_status(orc_heat),
    )


def _build_condenser_stage(orc_power: ResultEnvelope | None) -> DiagramStage:
    if orc_power is None:
        return DiagramStage("Air Condenser", "System eta pending", "", "idle")
    if orc_power.blocked_state.blocked:
        return _blocked_stage("Air Condenser", orc_power)
    system_eta = _metric_text(orc_power, "eta_system_gross", _format_percent, fallback="n/a")
    return DiagramStage("Air Condenser", f"eta sys {system_eta}", "Air cooled sink", _stage_status(orc_power))


def _build_organic_pump_stage(orc_power: ResultEnvelope | None) -> DiagramStage:
    if orc_power is None:
        return DiagramStage("Organic Pump", "Power basis pending", "", "idle")
    if orc_power.blocked_state.blocked:
        return _blocked_stage("Organic Pump", orc_power)
    mode_text = str(orc_power.metadata.get("calculation_mode", "")).replace("_", " ")
    return DiagramStage("Organic Pump", "Power basis", _shorten(mode_text, 24), _stage_status(orc_power))


def _blocked_stage(title: str, envelope: ResultEnvelope) -> DiagramStage:
    return DiagramStage(title, "BLOCKED", _shorten(envelope.blocked_state.reason or "No reason.", 28), "blocked")


def _metric_text(
    envelope: ResultEnvelope,
    key: str,
    formatter,
    *,
    fallback: str = "--",
) -> str:
    metric = envelope.values.get(key)
    if metric is None:
        return fallback
    return formatter(metric.value_si)


def _stream_temp_pair(stream: ProcessStream) -> str:
    inlet_c = k_to_c(stream.inlet.temp_k)
    outlet_c = k_to_c(stream.outlet.temp_k) if stream.outlet is not None and stream.outlet.temp_k is not None else None
    if outlet_c is None:
        return f"Tin {inlet_c:.0f} C"
    return f"T {inlet_c:.0f} -> {outlet_c:.0f} C"


def _format_power(value_w: float) -> str:
    return f"{value_w / 1000.0:,.1f} kW"


def _format_percent(value_fraction: float) -> str:
    return f"{100.0 * value_fraction:,.1f}%"


def _format_kelvin(value_k: float) -> str:
    return f"{value_k:,.1f} K"


def _stage_status(envelope: ResultEnvelope) -> str:
    return str(envelope.status.value if isinstance(envelope.status, ResultStatus) else envelope.status)


def _shorten(text: str, limit: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."
