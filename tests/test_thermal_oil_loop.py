from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.domain.models import FluidKind, FluidSpec, ProcessStream, PropertyBackend, PropertyModelSpec, StatePoint
from whrs_orc.domain.result_schema import ResultStatus
from whrs_orc.equipment.contracts import ThermalOilLoopMode, ThermalOilLoopRequest
from whrs_orc.equipment.thermal_oil_loop import solve_thermal_oil_loop


def c_to_k(temp_c: float) -> float:
    return temp_c + 273.15


def build_oil_stream(temp_c: float, *, name: str) -> ProcessStream:
    return ProcessStream(
        stream_id=name,
        display_name=name,
        fluid=FluidSpec(
            fluid_id="manual_oil",
            display_name="Manual Oil",
            kind=FluidKind.THERMAL_OIL,
            property_model=PropertyModelSpec(
                backend_id=PropertyBackend.MANUAL,
                payload={"cp_const_j_kg_k": 2200.0, "density_kg_m3": 880.0},
            ),
        ),
        mass_flow_kg_s=20.0,
        inlet=StatePoint(tag=f"{name}_in", temp_k=c_to_k(temp_c), pressure_pa=101325.0),
    )


class ThermalOilLoopTests(unittest.TestCase):
    def test_adiabatic_link_has_no_heat_loss(self) -> None:
        request = ThermalOilLoopRequest(
            equipment_id="loop",
            mode=ThermalOilLoopMode.ADIABATIC_LINK,
            oil_supply_stream=build_oil_stream(250.0, name="supply"),
            oil_return_stream=build_oil_stream(180.0, name="return"),
        )

        result = solve_thermal_oil_loop(request)

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(result.values["q_loop_loss_w"].value_si, 0.0, places=6)
        self.assertAlmostEqual(result.solved_streams["oil_delivered_stream"].outlet.temp_k, c_to_k(250.0), places=6)

    def test_rated_heat_loss_reduces_delivery_temperature(self) -> None:
        request = ThermalOilLoopRequest(
            equipment_id="loop",
            mode=ThermalOilLoopMode.RATED_HEAT_LOSS,
            oil_supply_stream=build_oil_stream(250.0, name="supply"),
            oil_return_stream=build_oil_stream(180.0, name="return"),
            parameters={"line_heat_loss_w": 440_000.0},
        )

        result = solve_thermal_oil_loop(request)

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(result.values["q_loop_loss_w"].value_si, 440_000.0, delta=10.0)
        self.assertAlmostEqual(result.values["delta_t_loop_k"].value_si, 10.0, places=2)


if __name__ == "__main__":
    unittest.main()
