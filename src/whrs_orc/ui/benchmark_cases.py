from __future__ import annotations

from dataclasses import dataclass

from whrs_orc.equipment.contracts import BoilerDesignDriver, BoilerMode, OrcScreeningHeatMode, OrcScreeningPowerMode, ThermalOilLoopMode
from whrs_orc.solvers.screening_case import ScreeningCaseInputs, c_to_k
from whrs_orc.ui.presets import DEFAULT_EXHAUST_COMPOSITION


@dataclass(frozen=True, slots=True)
class BenchmarkCaseDefinition:
    key: str
    display_name: str
    summary: str
    inputs: ScreeningCaseInputs


_BENCHMARK_CASES: tuple[BenchmarkCaseDefinition, ...] = (
    BenchmarkCaseDefinition(
        key="balanced_performance",
        display_name="Balanced Performance Baseline",
        summary="Measured performance case with balanced exhaust-to-oil duty and a clean ORC screening chain.",
        inputs=ScreeningCaseInputs(
            case_name="Benchmark - Balanced Performance",
            boiler_mode=BoilerMode.PERFORMANCE,
            exhaust_components=list(DEFAULT_EXHAUST_COMPOSITION),
            exhaust_mass_flow_kg_s=10.0,
            exhaust_inlet_temp_c=500.0,
            exhaust_outlet_temp_c=200.0,
            exhaust_pressure_pa=101_325.0,
            oil_name="Manual Oil",
            oil_cp_const_j_kg_k=2200.0,
            oil_density_kg_m3=880.0,
            oil_max_bulk_temp_c=320.0,
            oil_mass_flow_kg_s=20.0,
            oil_inlet_temp_c=175.0,
            oil_outlet_temp_c=250.0,
            loop_mode=ThermalOilLoopMode.ADIABATIC_LINK,
            loop_target_delivery_temp_c=245.0,
            loop_pressure_drop_pa=0.0,
            loop_pump_efficiency=0.75,
            wf_name="Cyclopentane Screening",
            wf_cp_const_j_kg_k=2000.0,
            wf_inlet_temp_c=100.0,
            wf_pressure_pa=200_000.0,
            wf_max_outlet_temp_c=170.0,
            orc_heat_mode=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
            orc_target_wf_outlet_temp_c=150.0,
            orc_known_heat_input_w=1_000_000.0,
            min_orc_approach_k=5.0,
            orc_power_mode=OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
            eta_orc_gross_target=0.18,
            gross_electric_power_target_w=400_000.0,
        ),
    ),
    BenchmarkCaseDefinition(
        key="high_recovery_performance",
        display_name="High Recovery Performance",
        summary="Hotter measured exhaust point with higher oil throughput and a stronger gross power estimate.",
        inputs=ScreeningCaseInputs(
            case_name="Benchmark - High Recovery Performance",
            boiler_mode=BoilerMode.PERFORMANCE,
            exhaust_components=list(DEFAULT_EXHAUST_COMPOSITION),
            exhaust_mass_flow_kg_s=12.0,
            exhaust_inlet_temp_c=520.0,
            exhaust_outlet_temp_c=230.0,
            exhaust_pressure_pa=101_325.0,
            oil_name="Manual Oil",
            oil_cp_const_j_kg_k=2200.0,
            oil_density_kg_m3=875.0,
            oil_max_bulk_temp_c=320.0,
            oil_mass_flow_kg_s=24.0,
            oil_inlet_temp_c=180.0,
            oil_outlet_temp_c=252.5,
            loop_mode=ThermalOilLoopMode.ADIABATIC_LINK,
            loop_target_delivery_temp_c=248.0,
            loop_pressure_drop_pa=12_000.0,
            loop_pump_efficiency=0.78,
            wf_name="Isopentane Screening",
            wf_cp_const_j_kg_k=2150.0,
            wf_inlet_temp_c=105.0,
            wf_pressure_pa=210_000.0,
            wf_max_outlet_temp_c=165.0,
            orc_heat_mode=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
            orc_target_wf_outlet_temp_c=150.0,
            orc_known_heat_input_w=1_000_000.0,
            min_orc_approach_k=6.0,
            orc_power_mode=OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
            eta_orc_gross_target=0.20,
            gross_electric_power_target_w=500_000.0,
        ),
    ),
    BenchmarkCaseDefinition(
        key="design_efficiency_target",
        display_name="Design Efficiency Target",
        summary="Design-mode benchmark where the user governs the boiler by a target efficiency instead of measured outlets.",
        inputs=ScreeningCaseInputs(
            case_name="Benchmark - Design Efficiency Target",
            boiler_mode=BoilerMode.DESIGN,
            boiler_design_driver=BoilerDesignDriver.TARGET_BOILER_EFFICIENCY,
            boiler_design_target_si=0.50,
            stack_min_temp_c=150.0,
            closure_tolerance_fraction=0.03,
            exhaust_components=list(DEFAULT_EXHAUST_COMPOSITION),
            exhaust_mass_flow_kg_s=10.0,
            exhaust_inlet_temp_c=500.0,
            exhaust_outlet_temp_c=None,
            exhaust_pressure_pa=101_325.0,
            oil_name="Manual Oil",
            oil_cp_const_j_kg_k=2200.0,
            oil_density_kg_m3=880.0,
            oil_max_bulk_temp_c=320.0,
            oil_mass_flow_kg_s=20.0,
            oil_inlet_temp_c=175.0,
            oil_outlet_temp_c=None,
            loop_mode=ThermalOilLoopMode.ADIABATIC_LINK,
            loop_target_delivery_temp_c=215.0,
            loop_pressure_drop_pa=0.0,
            loop_pump_efficiency=0.75,
            wf_name="Cyclopentane Screening",
            wf_cp_const_j_kg_k=2000.0,
            wf_inlet_temp_c=95.0,
            wf_pressure_pa=200_000.0,
            wf_max_outlet_temp_c=165.0,
            orc_heat_mode=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
            orc_target_wf_outlet_temp_c=145.0,
            orc_known_heat_input_w=1_000_000.0,
            min_orc_approach_k=5.0,
            orc_power_mode=OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
            eta_orc_gross_target=0.18,
            gross_electric_power_target_w=350_000.0,
        ),
    ),
)


def list_benchmark_cases() -> tuple[BenchmarkCaseDefinition, ...]:
    return _BENCHMARK_CASES


def get_benchmark_case(key: str) -> BenchmarkCaseDefinition:
    for case in _BENCHMARK_CASES:
        if case.key == key:
            return case
    raise KeyError(f"Unknown benchmark case `{key}`.")


def benchmark_display_map() -> dict[str, BenchmarkCaseDefinition]:
    return {case.display_name: case for case in _BENCHMARK_CASES}


def design_target_display_value(case: ScreeningCaseInputs) -> float | None:
    if case.boiler_design_driver is None or case.boiler_design_target_si is None:
        return None
    if case.boiler_design_driver in {
        BoilerDesignDriver.MINIMUM_STACK_TEMPERATURE,
        BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE,
    }:
        return case.boiler_design_target_si - 273.15
    return case.boiler_design_target_si
