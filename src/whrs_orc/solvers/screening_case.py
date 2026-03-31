from __future__ import annotations

from dataclasses import dataclass, field

from whrs_orc.domain.models import (
    ComponentFraction,
    CompositionSpec,
    FluidKind,
    FluidLimitSpec,
    FluidSpec,
    ProcessStream,
    PropertyBackend,
    PropertyModelSpec,
    StatePoint,
)
from whrs_orc.domain.result_schema import ResultEnvelope
from whrs_orc.equipment.contracts import (
    BoilerConstraints,
    BoilerDesignDriver,
    BoilerDesignTarget,
    BoilerMode,
    OrcHeaterStageTarget,
    OrcScreeningHeatConstraints,
    OrcScreeningHeatMode,
    OrcScreeningHeatRequest,
    OrcScreeningPowerMode,
    OrcScreeningPowerRequest,
    ThermalOilLoopMode,
    ThermalOilLoopRequest,
    WasteHeatBoilerRequest,
)
from whrs_orc.equipment.orc_screening_heat_uptake import solve_orc_screening_heat_uptake
from whrs_orc.equipment.orc_screening_power import solve_orc_screening_power
from whrs_orc.equipment.thermal_oil_loop import solve_thermal_oil_loop
from whrs_orc.equipment.waste_heat_boiler import solve_waste_heat_boiler


def c_to_k(temp_c: float) -> float:
    return temp_c + 273.15


def k_to_c(temp_k: float) -> float:
    return temp_k - 273.15


@dataclass(slots=True)
class OrcHeaterStageInput:
    stage_name: str
    duty_fraction: float | None = None
    target_wf_outlet_temp_c: float | None = None
    heat_input_w: float | None = None


@dataclass(slots=True)
class ScreeningCaseInputs:
    case_name: str = "Untitled Screening Case"
    boiler_mode: BoilerMode = BoilerMode.PERFORMANCE
    boiler_design_driver: BoilerDesignDriver | None = None
    boiler_design_target_si: float | None = None
    stack_min_temp_c: float = 150.0
    closure_tolerance_fraction: float = 0.03

    exhaust_components: list[tuple[str, float]] = field(default_factory=list)
    exhaust_mass_flow_kg_s: float = 10.0
    exhaust_inlet_temp_c: float = 500.0
    exhaust_outlet_temp_c: float | None = 200.0
    exhaust_pressure_pa: float = 101_325.0

    oil_name: str = "Manual Oil"
    oil_cp_const_j_kg_k: float = 2200.0
    oil_density_kg_m3: float = 880.0
    oil_max_bulk_temp_c: float = 320.0
    oil_mass_flow_kg_s: float = 20.0
    oil_inlet_temp_c: float = 175.0
    oil_outlet_temp_c: float | None = 250.0

    loop_mode: ThermalOilLoopMode = ThermalOilLoopMode.ADIABATIC_LINK
    loop_heat_loss_w: float = 0.0
    loop_target_delivery_temp_c: float = 245.0
    loop_pressure_drop_pa: float = 0.0
    loop_pump_efficiency: float = 0.75

    wf_name: str = "Cyclopentane Screening"
    wf_cp_const_j_kg_k: float = 2000.0
    wf_inlet_temp_c: float = 100.0
    wf_pressure_pa: float = 200_000.0
    wf_max_outlet_temp_c: float = 170.0

    orc_heat_mode: OrcScreeningHeatMode = OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE
    orc_heater_stage_count: int = 1
    orc_heater_stages: list[OrcHeaterStageInput] = field(default_factory=list)
    orc_target_wf_outlet_temp_c: float = 150.0
    orc_known_heat_input_w: float = 1_000_000.0
    min_orc_approach_k: float = 5.0

    orc_power_mode: OrcScreeningPowerMode = OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY
    eta_orc_gross_target: float = 0.18
    gross_electric_power_target_w: float = 400_000.0


@dataclass(slots=True)
class ScreeningCaseResult:
    boiler_result: ResultEnvelope
    loop_result: ResultEnvelope | None = None
    orc_heat_result: ResultEnvelope | None = None
    orc_power_result: ResultEnvelope | None = None


def run_screening_case(inputs: ScreeningCaseInputs) -> ScreeningCaseResult:
    exhaust_stream = _build_exhaust_stream(inputs)
    oil_stream = _build_oil_stream(inputs)

    design_target = None
    if inputs.boiler_mode is BoilerMode.DESIGN:
        if inputs.boiler_design_driver is None or inputs.boiler_design_target_si is None:
            raise ValueError("Design mode requires both `boiler_design_driver` and `boiler_design_target_si`.")
        target_unit = "1" if inputs.boiler_design_driver is BoilerDesignDriver.TARGET_BOILER_EFFICIENCY else "K"
        design_target = BoilerDesignTarget(
            design_driver=inputs.boiler_design_driver,
            target_value_si=inputs.boiler_design_target_si,
            target_unit_si=target_unit,
        )

    boiler_result = solve_waste_heat_boiler(
        WasteHeatBoilerRequest(
            equipment_id="boiler",
            mode=inputs.boiler_mode,
            exhaust_stream=exhaust_stream,
            oil_stream=oil_stream,
            constraints=BoilerConstraints(
                stack_min_temp_k=c_to_k(inputs.stack_min_temp_c),
                max_closure_fraction=inputs.closure_tolerance_fraction,
                max_oil_bulk_temp_k=c_to_k(inputs.oil_max_bulk_temp_c),
            ),
            design_target=design_target,
        )
    )
    if boiler_result.blocked_state.blocked:
        return ScreeningCaseResult(boiler_result=boiler_result)

    boiler_oil_stream = boiler_result.solved_streams["resolved_oil_stream"]
    oil_supply_inlet = boiler_oil_stream.outlet or boiler_oil_stream.inlet
    oil_supply_stream = ProcessStream(
        stream_id="oil_supply",
        display_name="Oil Supply From Boiler",
        fluid=boiler_oil_stream.fluid,
        mass_flow_kg_s=boiler_oil_stream.mass_flow_kg_s,
        inlet=oil_supply_inlet,
    )
    oil_return_stream = ProcessStream(
        stream_id="oil_return",
        display_name="Oil Return",
        fluid=oil_supply_stream.fluid,
        mass_flow_kg_s=oil_supply_stream.mass_flow_kg_s,
        inlet=StatePoint(tag="oil_return_in", temp_k=c_to_k(inputs.oil_inlet_temp_c), pressure_pa=oil_supply_stream.inlet.pressure_pa),
    )
    loop_result = solve_thermal_oil_loop(
        ThermalOilLoopRequest(
            equipment_id="thermal_oil_loop",
            mode=inputs.loop_mode,
            oil_supply_stream=oil_supply_stream,
            oil_return_stream=oil_return_stream,
            parameters={
                "line_heat_loss_w": inputs.loop_heat_loss_w,
                "line_pressure_drop_pa": inputs.loop_pressure_drop_pa,
                "pump_efficiency": inputs.loop_pump_efficiency,
                "target_delivery_temp_k": c_to_k(inputs.loop_target_delivery_temp_c),
            },
        )
    )
    if loop_result.blocked_state.blocked:
        return ScreeningCaseResult(boiler_result=boiler_result, loop_result=loop_result)

    oil_delivered_stream = loop_result.solved_streams["oil_delivered_stream"]
    oil_hot_stream = ProcessStream(
        stream_id="oil_to_orc",
        display_name="Oil To ORC",
        fluid=oil_delivered_stream.fluid,
        mass_flow_kg_s=oil_delivered_stream.mass_flow_kg_s,
        inlet=oil_delivered_stream.outlet or oil_delivered_stream.inlet,
        outlet=oil_return_stream.inlet if inputs.orc_heat_mode is OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE else None,
    )
    wf_stream = _build_working_fluid_stream(inputs)

    heater_stage_inputs = _resolve_orc_heater_stages(inputs)
    heater_stage_targets = [
        OrcHeaterStageTarget(
            stage_name=stage.stage_name,
            duty_fraction=stage.duty_fraction,
            target_wf_outlet_temp_k=c_to_k(stage.target_wf_outlet_temp_c) if stage.target_wf_outlet_temp_c is not None else None,
            heat_input_w=stage.heat_input_w,
        )
        for stage in heater_stage_inputs
    ]

    orc_heat_result = solve_orc_screening_heat_uptake(
        OrcScreeningHeatRequest(
            equipment_id="orc_heat",
            mode=inputs.orc_heat_mode,
            oil_hot_stream=oil_hot_stream,
            wf_cold_stream=wf_stream,
            heater_stages=heater_stage_targets,
            constraints=OrcScreeningHeatConstraints(
                min_approach_delta_t_k=inputs.min_orc_approach_k,
                max_wf_outlet_temp_k=c_to_k(inputs.wf_max_outlet_temp_c),
            ),
            case_context={"heater_stage_count": len(heater_stage_targets)},
        )
    )
    if orc_heat_result.blocked_state.blocked:
        return ScreeningCaseResult(boiler_result=boiler_result, loop_result=loop_result, orc_heat_result=orc_heat_result)

    q_exhaust_available = boiler_result.values["q_exhaust_available_w"].value_si
    q_orc_absorbed = orc_heat_result.values["q_orc_absorbed_w"].value_si
    orc_power_result = solve_orc_screening_power(
        OrcScreeningPowerRequest(
            equipment_id="orc_power",
            mode=inputs.orc_power_mode,
            q_orc_absorbed_w=q_orc_absorbed,
            eta_orc_gross_target=inputs.eta_orc_gross_target if inputs.orc_power_mode is OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY else None,
            gross_electric_power_target_w=inputs.gross_electric_power_target_w if inputs.orc_power_mode is OrcScreeningPowerMode.GROSS_EFFICIENCY_FROM_POWER else None,
            q_exhaust_available_w=q_exhaust_available,
        )
    )

    return ScreeningCaseResult(
        boiler_result=boiler_result,
        loop_result=loop_result,
        orc_heat_result=orc_heat_result,
        orc_power_result=orc_power_result,
    )


def _build_exhaust_stream(inputs: ScreeningCaseInputs) -> ProcessStream:
    composition = CompositionSpec(
        components=[ComponentFraction(component_id=component_id, fraction=fraction) for component_id, fraction in inputs.exhaust_components]
    )
    return ProcessStream(
        stream_id="exhaust_hot",
        display_name="Exhaust Hot Stream",
        fluid=FluidSpec(
            fluid_id="site_exhaust",
            display_name="Site Exhaust",
            kind=FluidKind.EXHAUST_GAS,
            property_model=PropertyModelSpec(backend_id=PropertyBackend.AUTO),
            composition=composition,
        ),
        mass_flow_kg_s=inputs.exhaust_mass_flow_kg_s,
        inlet=StatePoint(tag="exhaust_in", temp_k=c_to_k(inputs.exhaust_inlet_temp_c), pressure_pa=inputs.exhaust_pressure_pa),
        outlet=StatePoint(tag="exhaust_out", temp_k=c_to_k(inputs.exhaust_outlet_temp_c), pressure_pa=inputs.exhaust_pressure_pa) if inputs.exhaust_outlet_temp_c is not None else None,
    )


def _build_oil_stream(inputs: ScreeningCaseInputs) -> ProcessStream:
    return ProcessStream(
        stream_id="oil_loop",
        display_name="Thermal Oil",
        fluid=FluidSpec(
            fluid_id=inputs.oil_name,
            display_name=inputs.oil_name,
            kind=FluidKind.THERMAL_OIL,
            property_model=PropertyModelSpec(
                backend_id=PropertyBackend.MANUAL if inputs.oil_name == "Manual Oil" else PropertyBackend.CORRELATION,
                payload={
                    "cp_const_j_kg_k": inputs.oil_cp_const_j_kg_k,
                    "density_kg_m3": inputs.oil_density_kg_m3,
                }
                if inputs.oil_name == "Manual Oil"
                else {},
            ),
            limits=FluidLimitSpec(max_bulk_temp_k=c_to_k(inputs.oil_max_bulk_temp_c)),
        ),
        mass_flow_kg_s=inputs.oil_mass_flow_kg_s,
        inlet=StatePoint(tag="oil_in", temp_k=c_to_k(inputs.oil_inlet_temp_c), pressure_pa=101_325.0),
        outlet=StatePoint(tag="oil_out", temp_k=c_to_k(inputs.oil_outlet_temp_c), pressure_pa=101_325.0) if inputs.oil_outlet_temp_c is not None else None,
    )


def _build_working_fluid_stream(inputs: ScreeningCaseInputs) -> ProcessStream:
    metadata = {}
    backend = PropertyBackend.MANUAL
    payload = {"cp_const_j_kg_k": inputs.wf_cp_const_j_kg_k}
    if inputs.wf_name.lower() not in {"manual wf", "manual working fluid"}:
        backend = PropertyBackend.MANUAL
    return ProcessStream(
        stream_id="wf_cold",
        display_name=inputs.wf_name,
        fluid=FluidSpec(
            fluid_id=inputs.wf_name,
            display_name=inputs.wf_name,
            kind=FluidKind.WORKING_FLUID,
            property_model=PropertyModelSpec(backend_id=backend, payload=payload),
            limits=FluidLimitSpec(max_bulk_temp_k=c_to_k(inputs.wf_max_outlet_temp_c)),
            metadata=metadata,
        ),
        mass_flow_kg_s=max(inputs.oil_mass_flow_kg_s * 0.5, 1.0),
        inlet=StatePoint(tag="wf_in", temp_k=c_to_k(inputs.wf_inlet_temp_c), pressure_pa=inputs.wf_pressure_pa),
    )


def _resolve_orc_heater_stages(inputs: ScreeningCaseInputs) -> list[OrcHeaterStageInput]:
    stage_count = max(1, int(inputs.orc_heater_stage_count or 1))
    defaults = _default_orc_heater_stage_inputs(inputs, stage_count)
    if not inputs.orc_heater_stages:
        return defaults

    resolved: list[OrcHeaterStageInput] = []
    for index in range(stage_count):
        if index < len(inputs.orc_heater_stages):
            stage = inputs.orc_heater_stages[index]
            default_stage = defaults[index]
            resolved.append(
                OrcHeaterStageInput(
                    stage_name=stage.stage_name.strip() or default_stage.stage_name,
                    duty_fraction=stage.duty_fraction if stage.duty_fraction is not None else default_stage.duty_fraction,
                    target_wf_outlet_temp_c=(
                        stage.target_wf_outlet_temp_c
                        if stage.target_wf_outlet_temp_c is not None
                        else default_stage.target_wf_outlet_temp_c
                    ),
                    heat_input_w=stage.heat_input_w if stage.heat_input_w is not None else default_stage.heat_input_w,
                )
            )
        else:
            resolved.append(defaults[index])
    return resolved


def _default_orc_heater_stage_inputs(inputs: ScreeningCaseInputs, stage_count: int) -> list[OrcHeaterStageInput]:
    names = _default_orc_heater_stage_names(stage_count)
    if inputs.orc_heat_mode is OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE:
        share = 1.0 / stage_count
        return [OrcHeaterStageInput(stage_name=name, duty_fraction=share) for name in names]

    if inputs.orc_heat_mode is OrcScreeningHeatMode.SINGLE_PHASE_TEMPERATURE_GAIN:
        final_temp_c = max(inputs.orc_target_wf_outlet_temp_c, inputs.wf_inlet_temp_c + 1.0)
        delta_c = final_temp_c - inputs.wf_inlet_temp_c
        return [
            OrcHeaterStageInput(
                stage_name=name,
                target_wf_outlet_temp_c=inputs.wf_inlet_temp_c + delta_c * ((index + 1) / stage_count),
            )
            for index, name in enumerate(names)
        ]

    share_w = inputs.orc_known_heat_input_w / stage_count
    return [OrcHeaterStageInput(stage_name=name, heat_input_w=share_w) for name in names]


def _default_orc_heater_stage_names(stage_count: int) -> list[str]:
    defaults = ["ORC Heater"]
    if stage_count == 2:
        defaults = ["Preheater", "Vaporizer"]
    elif stage_count == 3:
        defaults = ["Preheater", "Vaporizer", "Superheater"]
    elif stage_count >= 4:
        defaults = ["Preheater", "Vaporizer", "Superheater"]
        defaults.extend(f"Stage {index}" for index in range(4, stage_count + 1))
    if stage_count == 1:
        return defaults
    return defaults[:stage_count]
