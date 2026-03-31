from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.domain.models import FluidKind, FluidLimitSpec, FluidSpec, ProcessStream, PropertyBackend, PropertyModelSpec, StatePoint
from whrs_orc.domain.result_schema import ResultStatus
from whrs_orc.equipment.contracts import (
    OrcHeaterStageTarget,
    OrcScreeningHeatConstraints,
    OrcScreeningHeatMode,
    OrcScreeningHeatRequest,
    OrcScreeningPowerMode,
    OrcScreeningPowerRequest,
)
from whrs_orc.equipment.orc_screening_heat_uptake import solve_orc_screening_heat_uptake
from whrs_orc.equipment.orc_screening_power import solve_orc_screening_power


def c_to_k(temp_c: float) -> float:
    return temp_c + 273.15


def build_oil_hot_stream(*, include_outlet: bool) -> ProcessStream:
    return ProcessStream(
        stream_id="oil_hot",
        display_name="Oil Hot",
        fluid=FluidSpec(
            fluid_id="manual_oil",
            display_name="Manual Oil",
            kind=FluidKind.THERMAL_OIL,
            property_model=PropertyModelSpec(
                backend_id=PropertyBackend.MANUAL,
                payload={"cp_const_j_kg_k": 2200.0},
            ),
        ),
        mass_flow_kg_s=20.0,
        inlet=StatePoint(tag="oil_in", temp_k=c_to_k(250.0), pressure_pa=101325.0),
        outlet=StatePoint(tag="oil_out", temp_k=c_to_k(210.0), pressure_pa=101325.0) if include_outlet else None,
    )


def build_working_fluid_stream() -> ProcessStream:
    return ProcessStream(
        stream_id="wf",
        display_name="Cyclopentane Screening",
        fluid=FluidSpec(
            fluid_id="Cyclopentane",
            display_name="Cyclopentane Screening",
            kind=FluidKind.WORKING_FLUID,
            property_model=PropertyModelSpec(
                backend_id=PropertyBackend.MANUAL,
                payload={"cp_const_j_kg_k": 2000.0},
            ),
            limits=FluidLimitSpec(max_bulk_temp_k=c_to_k(170.0)),
        ),
        mass_flow_kg_s=10.0,
        inlet=StatePoint(tag="wf_in", temp_k=c_to_k(100.0), pressure_pa=200000.0),
    )


class OrcScreeningTests(unittest.TestCase):
    def test_screening_from_oil_side(self) -> None:
        request = OrcScreeningHeatRequest(
            equipment_id="orc_heat",
            mode=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
            oil_hot_stream=build_oil_hot_stream(include_outlet=True),
            wf_cold_stream=build_working_fluid_stream(),
            constraints=OrcScreeningHeatConstraints(min_approach_delta_t_k=5.0, max_wf_outlet_temp_k=c_to_k(170.0)),
        )

        result = solve_orc_screening_heat_uptake(request)

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(result.values["q_orc_absorbed_w"].value_si, 1_400_000.0, delta=15.0)
        self.assertAlmostEqual(result.values["wf_temp_gain_k"].value_si, 70.0, places=2)

    def test_single_phase_temperature_gain_blocks_when_limit_exceeded(self) -> None:
        request = OrcScreeningHeatRequest(
            equipment_id="orc_heat",
            mode=OrcScreeningHeatMode.SINGLE_PHASE_TEMPERATURE_GAIN,
            oil_hot_stream=build_oil_hot_stream(include_outlet=False),
            wf_cold_stream=build_working_fluid_stream(),
            constraints=OrcScreeningHeatConstraints(max_wf_outlet_temp_k=c_to_k(150.0)),
            parameters={"target_wf_outlet_temp_k": c_to_k(170.0)},
        )

        result = solve_orc_screening_heat_uptake(request)

        self.assertEqual(result.status, ResultStatus.BLOCKED)
        self.assertTrue(result.blocked_state.blocked)

    def test_multistage_oil_side_screening_tracks_stage_breakdown(self) -> None:
        request = OrcScreeningHeatRequest(
            equipment_id="orc_heat",
            mode=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
            oil_hot_stream=build_oil_hot_stream(include_outlet=True),
            wf_cold_stream=build_working_fluid_stream(),
            heater_stages=[
                OrcHeaterStageTarget(stage_name="Preheater", duty_fraction=0.25),
                OrcHeaterStageTarget(stage_name="Vaporizer", duty_fraction=0.75),
            ],
            constraints=OrcScreeningHeatConstraints(min_approach_delta_t_k=5.0, max_wf_outlet_temp_k=c_to_k(200.0)),
        )

        result = solve_orc_screening_heat_uptake(request)

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.metadata["heater_stage_count"], 2)
        self.assertEqual(len(result.metadata["stage_breakdown"]), 2)
        self.assertIn("resolved_wf_stage_2", result.solved_streams)

    def test_gross_power_from_efficiency(self) -> None:
        request = OrcScreeningPowerRequest(
            equipment_id="orc_power",
            mode=OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
            q_orc_absorbed_w=2_000_000.0,
            eta_orc_gross_target=0.2,
            q_exhaust_available_w=5_000_000.0,
        )

        result = solve_orc_screening_power(request)

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(result.values["gross_electric_power_w"].value_si, 400_000.0, places=2)
        self.assertAlmostEqual(result.values["eta_system_gross"].value_si, 0.08, places=6)

    def test_gross_efficiency_blocks_when_power_exceeds_heat(self) -> None:
        request = OrcScreeningPowerRequest(
            equipment_id="orc_power",
            mode=OrcScreeningPowerMode.GROSS_EFFICIENCY_FROM_POWER,
            q_orc_absorbed_w=1_000_000.0,
            gross_electric_power_target_w=1_200_000.0,
        )

        result = solve_orc_screening_power(request)

        self.assertEqual(result.status, ResultStatus.BLOCKED)
        self.assertTrue(result.blocked_state.blocked)


if __name__ == "__main__":
    unittest.main()
