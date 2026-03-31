from __future__ import annotations

from datetime import UTC, datetime
import re

from whrs_orc import __version__
from whrs_orc.domain.result_schema import ResultEnvelope
from whrs_orc.solvers.screening_case import ScreeningCaseInputs, ScreeningCaseResult
from whrs_orc.ui.operator_guidance import build_operator_guidance


def build_screening_report_payload(
    case: ScreeningCaseInputs,
    result: ScreeningCaseResult,
    *,
    generated_at_utc: datetime | None = None,
) -> dict[str, object]:
    timestamp = generated_at_utc or datetime.now(UTC)
    return {
        "report_meta": {
            "report_type": "screening_case",
            "generated_at_utc": timestamp.isoformat(),
            "app_version": __version__,
            "case_name": case.case_name,
        },
        "case_inputs": _case_inputs_to_dict(case),
        "kpis": _kpi_summary(result),
        "operator_guidance": [
            {
                "severity": note.severity,
                "title": note.title,
                "detail": note.detail,
            }
            for note in build_operator_guidance(result)
        ],
        "results": {
            "boiler": _envelope_to_dict(result.boiler_result),
            "oil_loop": _envelope_to_dict(result.loop_result),
            "orc_heat": _envelope_to_dict(result.orc_heat_result),
            "orc_power": _envelope_to_dict(result.orc_power_result),
        },
    }


def build_screening_markdown_report(
    case: ScreeningCaseInputs,
    result: ScreeningCaseResult,
    *,
    generated_at_utc: datetime | None = None,
) -> str:
    payload = build_screening_report_payload(case, result, generated_at_utc=generated_at_utc)
    lines = [
        "# WHRS ORC Screening Report",
        "",
        f"- Case name: {case.case_name}",
        f"- Generated at UTC: {payload['report_meta']['generated_at_utc']}",
        f"- App version: {payload['report_meta']['app_version']}",
        "",
        "## Study Definition",
        "",
        f"- Boiler mode: {case.boiler_mode.value}",
        f"- Boiler design driver: {case.boiler_design_driver.value if case.boiler_design_driver else '-'}",
        f"- Stack minimum temperature [degC]: {case.stack_min_temp_c}",
        f"- Closure tolerance [-]: {case.closure_tolerance_fraction}",
        f"- Exhaust mass flow [kg/s]: {case.exhaust_mass_flow_kg_s}",
        f"- Exhaust inlet temperature [degC]: {case.exhaust_inlet_temp_c}",
        f"- Exhaust outlet temperature [degC]: {case.exhaust_outlet_temp_c if case.exhaust_outlet_temp_c is not None else '-'}",
        f"- Thermal oil: {case.oil_name}",
        f"- Oil mass flow [kg/s]: {case.oil_mass_flow_kg_s}",
        f"- Oil inlet temperature [degC]: {case.oil_inlet_temp_c}",
        f"- Oil outlet temperature [degC]: {case.oil_outlet_temp_c if case.oil_outlet_temp_c is not None else '-'}",
        f"- ORC working fluid: {case.wf_name}",
        f"- ORC heat mode: {case.orc_heat_mode.value}",
        f"- ORC heater stage count: {case.orc_heater_stage_count}",
        f"- ORC power mode: {case.orc_power_mode.value}",
        "",
        "## KPI Summary",
        "",
    ]
    if case.orc_heater_stages:
        lines.extend(["- ORC heater stages:"])
        for stage in case.orc_heater_stages:
            stage_parts = [stage.stage_name]
            if stage.duty_fraction is not None:
                stage_parts.append(f"duty split {100.0 * stage.duty_fraction:.1f}%")
            if stage.target_wf_outlet_temp_c is not None:
                stage_parts.append(f"WF Tout {stage.target_wf_outlet_temp_c:.1f} degC")
            if stage.heat_input_w is not None:
                stage_parts.append(f"Q {stage.heat_input_w / 1000.0:.1f} kW")
            lines.append(f"  - {', '.join(stage_parts)}")
        lines.append("")
    for key, value in payload["kpis"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Operator Guidance", ""])
    guidance = payload["operator_guidance"]
    if guidance:
        for note in guidance:
            lines.append(f"- [{note['severity'].upper()}] {note['title']}: {note['detail']}")
    else:
        lines.append("- No operator guidance.")

    lines.extend(["", "## Module Results", ""])
    for label, envelope in [
        ("Boiler", result.boiler_result),
        ("Oil Loop", result.loop_result),
        ("ORC Heat", result.orc_heat_result),
        ("ORC Power", result.orc_power_result),
    ]:
        lines.append(f"### {label}")
        if envelope is None:
            lines.append("- Not solved.")
            lines.append("")
            continue
        lines.append(f"- Status: {envelope.status}")
        if envelope.blocked_state.blocked:
            lines.append(f"- Blocked reason: {envelope.blocked_state.reason}")
            if envelope.blocked_state.suggested_action:
                lines.append(f"- Suggested action: {envelope.blocked_state.suggested_action}")
        if envelope.values:
            lines.append("- Metrics:")
            for metric in envelope.values.values():
                lines.append(f"  - {metric.display_name}: {_format_metric(metric.key, metric.value_si)}")
        if envelope.warnings:
            lines.append("- Warnings:")
            for warning in envelope.warnings:
                lines.append(f"  - {warning.code}: {warning.message}")
        if envelope.assumptions:
            lines.append("- Assumptions:")
            for assumption in envelope.assumptions:
                lines.append(f"  - {assumption.code}: {assumption.message}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def default_report_filename(case_name: str, extension: str) -> str:
    safe_extension = extension.lstrip(".")
    return f"{slugify_case_name(case_name)}.{safe_extension}"


def slugify_case_name(case_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", case_name.strip().lower()).strip("-")
    return slug or "whrs-orc-case"


def _case_inputs_to_dict(case: ScreeningCaseInputs) -> dict[str, object]:
    return {
        "case_name": case.case_name,
        "boiler_mode": case.boiler_mode.value,
        "boiler_design_driver": case.boiler_design_driver.value if case.boiler_design_driver else None,
        "boiler_design_target_si": case.boiler_design_target_si,
        "stack_min_temp_c": case.stack_min_temp_c,
        "closure_tolerance_fraction": case.closure_tolerance_fraction,
        "exhaust_components": [
            {
                "component_id": component_id,
                "fraction": fraction,
            }
            for component_id, fraction in case.exhaust_components
        ],
        "exhaust_mass_flow_kg_s": case.exhaust_mass_flow_kg_s,
        "exhaust_inlet_temp_c": case.exhaust_inlet_temp_c,
        "exhaust_outlet_temp_c": case.exhaust_outlet_temp_c,
        "exhaust_pressure_pa": case.exhaust_pressure_pa,
        "oil_name": case.oil_name,
        "oil_cp_const_j_kg_k": case.oil_cp_const_j_kg_k,
        "oil_density_kg_m3": case.oil_density_kg_m3,
        "oil_max_bulk_temp_c": case.oil_max_bulk_temp_c,
        "oil_mass_flow_kg_s": case.oil_mass_flow_kg_s,
        "oil_inlet_temp_c": case.oil_inlet_temp_c,
        "oil_outlet_temp_c": case.oil_outlet_temp_c,
        "loop_mode": case.loop_mode.value,
        "loop_heat_loss_w": case.loop_heat_loss_w,
        "loop_target_delivery_temp_c": case.loop_target_delivery_temp_c,
        "loop_pressure_drop_pa": case.loop_pressure_drop_pa,
        "loop_pump_efficiency": case.loop_pump_efficiency,
        "wf_name": case.wf_name,
        "wf_cp_const_j_kg_k": case.wf_cp_const_j_kg_k,
        "wf_inlet_temp_c": case.wf_inlet_temp_c,
        "wf_pressure_pa": case.wf_pressure_pa,
        "wf_max_outlet_temp_c": case.wf_max_outlet_temp_c,
        "orc_heat_mode": case.orc_heat_mode.value,
        "orc_heater_stage_count": case.orc_heater_stage_count,
        "orc_heater_stages": [
            {
                "stage_name": stage.stage_name,
                "duty_fraction": stage.duty_fraction,
                "target_wf_outlet_temp_c": stage.target_wf_outlet_temp_c,
                "heat_input_w": stage.heat_input_w,
            }
            for stage in case.orc_heater_stages
        ],
        "orc_target_wf_outlet_temp_c": case.orc_target_wf_outlet_temp_c,
        "orc_known_heat_input_w": case.orc_known_heat_input_w,
        "min_orc_approach_k": case.min_orc_approach_k,
        "orc_power_mode": case.orc_power_mode.value,
        "eta_orc_gross_target": case.eta_orc_gross_target,
        "gross_electric_power_target_w": case.gross_electric_power_target_w,
    }


def _kpi_summary(result: ScreeningCaseResult) -> dict[str, str]:
    values: dict[str, str] = {}
    for envelope in [result.boiler_result, result.loop_result, result.orc_heat_result, result.orc_power_result]:
        if envelope is None:
            continue
        for key, metric in envelope.values.items():
            if key in {
                "q_exhaust_available_w",
                "q_boiler_transferred_w",
                "q_orc_absorbed_w",
                "gross_electric_power_w",
                "eta_boiler",
                "eta_system_gross",
                "eta_orc_gross",
                "min_delta_t_k",
                "closure_ratio",
            }:
                values[key] = _format_metric(key, metric.value_si)
    return values


def _envelope_to_dict(envelope: ResultEnvelope | None) -> dict[str, object] | None:
    if envelope is None:
        return None
    return envelope.to_dict()


def _format_metric(key: str, value: float) -> str:
    if key.endswith("_w"):
        return f"{value / 1000.0:,.1f} kW"
    if key.endswith("_k"):
        return f"{value:,.2f} K"
    if key.startswith("eta_") or key.endswith("_ratio"):
        return f"{100.0 * value:,.2f} %"
    return f"{value:,.4g}"
