from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.equipment.contracts import BoilerMode, OrcScreeningHeatMode, OrcScreeningPowerMode, ThermalOilLoopMode
from whrs_orc.solvers.screening_case import ScreeningCaseInputs, c_to_k, run_screening_case
from whrs_orc.ui.presets import DEFAULT_EXHAUST_COMPOSITION


class ScreeningCaseTests(unittest.TestCase):
    def test_full_performance_chain_returns_gross_power(self) -> None:
        result = run_screening_case(
            ScreeningCaseInputs(
                case_name="performance-case",
                boiler_mode=BoilerMode.PERFORMANCE,
                exhaust_components=DEFAULT_EXHAUST_COMPOSITION,
                exhaust_mass_flow_kg_s=10.0,
                exhaust_inlet_temp_c=500.0,
                exhaust_outlet_temp_c=200.0,
                oil_name="Manual Oil",
                oil_mass_flow_kg_s=20.0,
                oil_inlet_temp_c=175.0,
                oil_outlet_temp_c=250.0,
                loop_mode=ThermalOilLoopMode.ADIABATIC_LINK,
                wf_name="Cyclopentane Screening",
                orc_heat_mode=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
                orc_power_mode=OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
                eta_orc_gross_target=0.18,
            )
        )

        self.assertFalse(result.boiler_result.blocked_state.blocked)
        self.assertFalse(result.loop_result.blocked_state.blocked)
        self.assertFalse(result.orc_heat_result.blocked_state.blocked)
        self.assertFalse(result.orc_power_result.blocked_state.blocked)
        self.assertAlmostEqual(result.orc_power_result.values["gross_electric_power_w"].value_si, 252_000.0, delta=1.0)

    def test_loop_target_delivery_temperature_feeds_loop_solver(self) -> None:
        result = run_screening_case(
            ScreeningCaseInputs(
                case_name="loop-delivery-case",
                boiler_mode=BoilerMode.PERFORMANCE,
                exhaust_components=DEFAULT_EXHAUST_COMPOSITION,
                exhaust_mass_flow_kg_s=10.0,
                exhaust_inlet_temp_c=500.0,
                exhaust_outlet_temp_c=200.0,
                oil_name="Manual Oil",
                oil_mass_flow_kg_s=20.0,
                oil_inlet_temp_c=175.0,
                oil_outlet_temp_c=250.0,
                loop_mode=ThermalOilLoopMode.TARGET_DELIVERY_TEMPERATURE,
                loop_target_delivery_temp_c=230.0,
                wf_name="Cyclopentane Screening",
                orc_heat_mode=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
                orc_power_mode=OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
            )
        )

        delivered_stream = result.loop_result.solved_streams["oil_delivered_stream"]
        self.assertAlmostEqual(delivered_stream.outlet.temp_k, c_to_k(230.0), places=4)


if __name__ == "__main__":
    unittest.main()
