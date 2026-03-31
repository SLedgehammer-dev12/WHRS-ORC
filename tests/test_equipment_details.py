from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.equipment.contracts import BoilerMode, OrcScreeningHeatMode, OrcScreeningPowerMode, ThermalOilLoopMode
from whrs_orc.solvers.screening_case import ScreeningCaseInputs, run_screening_case
from whrs_orc.ui.equipment_details import build_equipment_details, build_idle_equipment_details, render_equipment_detail
from whrs_orc.ui.presets import DEFAULT_EXHAUST_COMPOSITION


class EquipmentDetailsTests(unittest.TestCase):
    def test_idle_detail_map_is_available(self) -> None:
        details = build_idle_equipment_details()

        self.assertIn("boiler", details)
        self.assertEqual(details["boiler"].status, "idle")

    def test_successful_case_builds_generator_detail(self) -> None:
        result = run_screening_case(
            ScreeningCaseInputs(
                case_name="detail-case",
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

        details = build_equipment_details(result)

        self.assertIn("generator", details)
        self.assertEqual(details["generator"].status, "success")
        self.assertIn("Gross electric power", render_equipment_detail(details["generator"]))


if __name__ == "__main__":
    unittest.main()
