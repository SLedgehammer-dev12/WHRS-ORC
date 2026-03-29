from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.domain.result_schema import ResultStatus
from whrs_orc.domain.models import FluidKind, FluidSpec, ProcessStream, PropertyBackend, PropertyModelSpec, StatePoint
from whrs_orc.equipment.contracts import (
    BoilerConstraints,
    BoilerDesignDriver,
    BoilerDesignTarget,
    BoilerMode,
    WasteHeatBoilerRequest,
)
from whrs_orc.equipment.waste_heat_boiler import solve_waste_heat_boiler


def c_to_k(temp_c: float) -> float:
    return temp_c + 273.15


def build_manual_exhaust(*, include_outlet: bool = True) -> ProcessStream:
    return ProcessStream(
        stream_id="exhaust",
        display_name="Exhaust",
        fluid=FluidSpec(
            fluid_id="manual_exhaust",
            display_name="Manual Exhaust",
            kind=FluidKind.EXHAUST_GAS,
            property_model=PropertyModelSpec(
                backend_id=PropertyBackend.MANUAL,
                payload={"cp_const_j_kg_k": 1100.0},
            ),
        ),
        mass_flow_kg_s=10.0,
        inlet=StatePoint(tag="g_in", temp_k=c_to_k(500.0), pressure_pa=101325.0),
        outlet=StatePoint(tag="g_out", temp_k=c_to_k(200.0), pressure_pa=101325.0) if include_outlet else None,
    )


def build_manual_oil(*, include_outlet: bool = True) -> ProcessStream:
    return ProcessStream(
        stream_id="oil",
        display_name="Oil",
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
        inlet=StatePoint(tag="o_in", temp_k=c_to_k(175.0), pressure_pa=101325.0),
        outlet=StatePoint(tag="o_out", temp_k=c_to_k(250.0), pressure_pa=101325.0) if include_outlet else None,
    )


class WasteHeatBoilerTests(unittest.TestCase):
    def test_performance_mode_balanced_case(self) -> None:
        request = WasteHeatBoilerRequest(
            equipment_id="boiler",
            mode=BoilerMode.PERFORMANCE,
            exhaust_stream=build_manual_exhaust(),
            oil_stream=build_manual_oil(),
            constraints=BoilerConstraints(stack_min_temp_k=c_to_k(150.0), max_closure_fraction=0.01),
        )

        result = solve_waste_heat_boiler(request)

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(result.values["q_exhaust_available_w"].value_si, 3_850_000.0, places=2)
        self.assertAlmostEqual(result.values["q_boiler_transferred_w"].value_si, 3_300_000.0, places=2)
        self.assertAlmostEqual(result.values["q_oil_absorbed_w"].value_si, 3_300_000.0, places=2)

    def test_design_mode_target_efficiency(self) -> None:
        request = WasteHeatBoilerRequest(
            equipment_id="boiler",
            mode=BoilerMode.DESIGN,
            exhaust_stream=build_manual_exhaust(include_outlet=False),
            oil_stream=build_manual_oil(include_outlet=False),
            constraints=BoilerConstraints(stack_min_temp_k=c_to_k(150.0), max_closure_fraction=0.01),
            design_target=BoilerDesignTarget(
                design_driver=BoilerDesignDriver.TARGET_BOILER_EFFICIENCY,
                target_value_si=0.5,
                target_unit_si="1",
            ),
        )

        result = solve_waste_heat_boiler(request)

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(result.values["q_exhaust_available_w"].value_si, 3_850_000.0, places=2)
        self.assertAlmostEqual(result.values["q_oil_absorbed_w"].value_si, 1_925_000.0, places=2)
        self.assertAlmostEqual(result.solved_streams["resolved_oil_stream"].outlet.temp_k, c_to_k(218.75), places=2)

    def test_design_mode_target_oil_outlet_temperature(self) -> None:
        request = WasteHeatBoilerRequest(
            equipment_id="boiler",
            mode=BoilerMode.DESIGN,
            exhaust_stream=build_manual_exhaust(include_outlet=False),
            oil_stream=build_manual_oil(include_outlet=False),
            constraints=BoilerConstraints(stack_min_temp_k=c_to_k(150.0), max_closure_fraction=0.01),
            design_target=BoilerDesignTarget(
                design_driver=BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE,
                target_value_si=c_to_k(250.0),
                target_unit_si="K",
            ),
        )

        result = solve_waste_heat_boiler(request)

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(result.values["q_oil_absorbed_w"].value_si, 3_300_000.0, places=2)

    def test_design_mode_missing_driver_blocks(self) -> None:
        request = WasteHeatBoilerRequest(
            equipment_id="boiler",
            mode=BoilerMode.DESIGN,
            exhaust_stream=build_manual_exhaust(include_outlet=False),
            oil_stream=build_manual_oil(include_outlet=False),
            constraints=BoilerConstraints(stack_min_temp_k=c_to_k(150.0)),
        )

        result = solve_waste_heat_boiler(request)

        self.assertEqual(result.status, ResultStatus.BLOCKED)
        self.assertTrue(result.blocked_state.blocked)

    def test_design_mode_unimplemented_driver_blocks(self) -> None:
        request = WasteHeatBoilerRequest(
            equipment_id="boiler",
            mode=BoilerMode.DESIGN,
            exhaust_stream=build_manual_exhaust(include_outlet=False),
            oil_stream=build_manual_oil(include_outlet=False),
            constraints=BoilerConstraints(stack_min_temp_k=c_to_k(150.0)),
            design_target=BoilerDesignTarget(
                design_driver=BoilerDesignDriver.TARGET_TRANSFERRED_POWER,
                target_value_si=1_000_000.0,
                target_unit_si="W",
            ),
        )

        result = solve_waste_heat_boiler(request)

        self.assertEqual(result.status, ResultStatus.BLOCKED)
        self.assertTrue(result.blocked_state.blocked)

    def test_performance_mode_blocks_negative_temperature_approach(self) -> None:
        hot_exhaust = build_manual_exhaust()
        hot_oil = ProcessStream(
            stream_id="oil_bad",
            display_name="Oil Bad",
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
            inlet=StatePoint(tag="o_in_bad", temp_k=c_to_k(290.0), pressure_pa=101325.0),
            outlet=StatePoint(tag="o_out_bad", temp_k=c_to_k(320.0), pressure_pa=101325.0),
        )
        request = WasteHeatBoilerRequest(
            equipment_id="boiler",
            mode=BoilerMode.PERFORMANCE,
            exhaust_stream=hot_exhaust,
            oil_stream=hot_oil,
            constraints=BoilerConstraints(stack_min_temp_k=c_to_k(150.0), max_closure_fraction=1.0),
        )

        result = solve_waste_heat_boiler(request)

        self.assertEqual(result.status, ResultStatus.BLOCKED)
        self.assertTrue(result.blocked_state.blocked)
        self.assertEqual(result.blocked_state.code, "VAL-HX-003")
        self.assertIsNotNone(result.blocked_state.suggested_action)


if __name__ == "__main__":
    unittest.main()
