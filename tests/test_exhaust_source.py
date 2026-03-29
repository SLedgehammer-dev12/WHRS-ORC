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
from whrs_orc.equipment.contracts import ExhaustSourceConstraints, ExhaustSourceMode, ExhaustSourceRequest
from whrs_orc.equipment.exhaust_source import solve_exhaust_source


def c_to_k(temp_c: float) -> float:
    return temp_c + 273.15


class ExhaustSourceTests(unittest.TestCase):
    def test_available_heat_from_stack_limit(self) -> None:
        exhaust = ProcessStream(
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
        )
        request = ExhaustSourceRequest(
            equipment_id="exhaust_source",
            mode=ExhaustSourceMode.AVAILABLE_HEAT_FROM_STACK_LIMIT,
            exhaust_stream=exhaust,
            constraints=ExhaustSourceConstraints(stack_min_temp_k=c_to_k(150.0)),
        )

        result = solve_exhaust_source(request)

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(result.values["available_heat_w"].value_si, 3_850_000.0, places=2)

    def test_released_heat_requires_outlet_temperature(self) -> None:
        exhaust = ProcessStream(
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
        )
        request = ExhaustSourceRequest(
            equipment_id="exhaust_source",
            mode=ExhaustSourceMode.RELEASED_HEAT_FROM_OUTLET_TEMPERATURE,
            exhaust_stream=exhaust,
        )

        result = solve_exhaust_source(request)

        self.assertEqual(result.status, ResultStatus.BLOCKED)
        self.assertTrue(result.blocked_state.blocked)


if __name__ == "__main__":
    unittest.main()

