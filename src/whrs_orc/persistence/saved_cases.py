from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re

from whrs_orc import __version__
from whrs_orc.equipment.contracts import BoilerDesignDriver, BoilerMode, OrcScreeningHeatMode, OrcScreeningPowerMode, ThermalOilLoopMode
from whrs_orc.solvers.screening_case import OrcHeaterStageInput, ScreeningCaseInputs


@dataclass(frozen=True, slots=True)
class SavedCaseDocument:
    schema_version: str
    saved_at_utc: str
    app_version: str
    case_inputs: ScreeningCaseInputs
    source_label: str | None = None
    note: str | None = None


def build_saved_case_document(
    case: ScreeningCaseInputs,
    *,
    source_label: str | None = None,
    note: str | None = None,
    saved_at_utc: datetime | None = None,
) -> SavedCaseDocument:
    timestamp = saved_at_utc or datetime.now(UTC)
    return SavedCaseDocument(
        schema_version="1.0",
        saved_at_utc=timestamp.isoformat(),
        app_version=__version__,
        case_inputs=case,
        source_label=source_label,
        note=note,
    )


def write_saved_case(
    path: str | Path,
    case: ScreeningCaseInputs,
    *,
    source_label: str | None = None,
    note: str | None = None,
    saved_at_utc: datetime | None = None,
) -> Path:
    document = build_saved_case_document(case, source_label=source_label, note=note, saved_at_utc=saved_at_utc)
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(saved_case_to_dict(document), indent=2, ensure_ascii=False), encoding="utf-8")
    return target_path


def read_saved_case(path: str | Path) -> SavedCaseDocument:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return saved_case_from_dict(payload)


def saved_case_to_dict(document: SavedCaseDocument) -> dict[str, object]:
    return {
        "schema_version": document.schema_version,
        "saved_at_utc": document.saved_at_utc,
        "app_version": document.app_version,
        "source_label": document.source_label,
        "note": document.note,
        "case_inputs": _case_inputs_to_dict(document.case_inputs),
    }


def saved_case_from_dict(payload: dict[str, object]) -> SavedCaseDocument:
    return SavedCaseDocument(
        schema_version=str(payload.get("schema_version", "1.0")),
        saved_at_utc=str(payload["saved_at_utc"]),
        app_version=str(payload["app_version"]),
        source_label=payload.get("source_label"),
        note=payload.get("note"),
        case_inputs=_case_inputs_from_dict(payload["case_inputs"]),
    )


def default_saved_case_filename(case_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", case_name.strip().lower()).strip("-")
    safe_slug = slug or "whrs-orc-case"
    return f"{safe_slug}.whrs.json"


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


def _case_inputs_from_dict(payload: dict[str, object]) -> ScreeningCaseInputs:
    return ScreeningCaseInputs(
        case_name=str(payload["case_name"]),
        boiler_mode=BoilerMode(str(payload["boiler_mode"])),
        boiler_design_driver=BoilerDesignDriver(str(payload["boiler_design_driver"])) if payload.get("boiler_design_driver") else None,
        boiler_design_target_si=float(payload["boiler_design_target_si"]) if payload.get("boiler_design_target_si") is not None else None,
        stack_min_temp_c=float(payload["stack_min_temp_c"]),
        closure_tolerance_fraction=float(payload["closure_tolerance_fraction"]),
        exhaust_components=[
            (str(item["component_id"]), float(item["fraction"]))
            for item in payload["exhaust_components"]
        ],
        exhaust_mass_flow_kg_s=float(payload["exhaust_mass_flow_kg_s"]),
        exhaust_inlet_temp_c=float(payload["exhaust_inlet_temp_c"]),
        exhaust_outlet_temp_c=float(payload["exhaust_outlet_temp_c"]) if payload.get("exhaust_outlet_temp_c") is not None else None,
        exhaust_pressure_pa=float(payload["exhaust_pressure_pa"]),
        oil_name=str(payload["oil_name"]),
        oil_cp_const_j_kg_k=float(payload["oil_cp_const_j_kg_k"]),
        oil_density_kg_m3=float(payload["oil_density_kg_m3"]),
        oil_max_bulk_temp_c=float(payload["oil_max_bulk_temp_c"]),
        oil_mass_flow_kg_s=float(payload["oil_mass_flow_kg_s"]),
        oil_inlet_temp_c=float(payload["oil_inlet_temp_c"]),
        oil_outlet_temp_c=float(payload["oil_outlet_temp_c"]) if payload.get("oil_outlet_temp_c") is not None else None,
        loop_mode=ThermalOilLoopMode(str(payload["loop_mode"])),
        loop_heat_loss_w=float(payload["loop_heat_loss_w"]),
        loop_target_delivery_temp_c=float(payload["loop_target_delivery_temp_c"]),
        loop_pressure_drop_pa=float(payload["loop_pressure_drop_pa"]),
        loop_pump_efficiency=float(payload["loop_pump_efficiency"]),
        wf_name=str(payload["wf_name"]),
        wf_cp_const_j_kg_k=float(payload["wf_cp_const_j_kg_k"]),
        wf_inlet_temp_c=float(payload["wf_inlet_temp_c"]),
        wf_pressure_pa=float(payload["wf_pressure_pa"]),
        wf_max_outlet_temp_c=float(payload["wf_max_outlet_temp_c"]),
        orc_heat_mode=OrcScreeningHeatMode(str(payload["orc_heat_mode"])),
        orc_heater_stage_count=int(payload.get("orc_heater_stage_count", 1)),
        orc_heater_stages=[
            OrcHeaterStageInput(
                stage_name=str(item["stage_name"]),
                duty_fraction=float(item["duty_fraction"]) if item.get("duty_fraction") is not None else None,
                target_wf_outlet_temp_c=(
                    float(item["target_wf_outlet_temp_c"]) if item.get("target_wf_outlet_temp_c") is not None else None
                ),
                heat_input_w=float(item["heat_input_w"]) if item.get("heat_input_w") is not None else None,
            )
            for item in payload.get("orc_heater_stages", [])
        ],
        orc_target_wf_outlet_temp_c=float(payload["orc_target_wf_outlet_temp_c"]),
        orc_known_heat_input_w=float(payload["orc_known_heat_input_w"]),
        min_orc_approach_k=float(payload["min_orc_approach_k"]),
        orc_power_mode=OrcScreeningPowerMode(str(payload["orc_power_mode"])),
        eta_orc_gross_target=float(payload["eta_orc_gross_target"]),
        gross_electric_power_target_w=float(payload["gross_electric_power_target_w"]),
    )
