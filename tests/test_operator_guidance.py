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
from whrs_orc.ui.operator_guidance import build_operator_guidance, render_operator_guidance
from whrs_orc.ui.presets import DEFAULT_EXHAUST_COMPOSITION


class OperatorGuidanceTests(unittest.TestCase):
    def test_negative_boiler_temperature_approach_returns_critical_guidance(self) -> None:
        result = run_screening_case(
            ScreeningCaseInputs(
                case_name="blocked-guidance",
                boiler_mode=BoilerMode.PERFORMANCE,
                exhaust_components=DEFAULT_EXHAUST_COMPOSITION,
                exhaust_mass_flow_kg_s=10.0,
                exhaust_inlet_temp_c=500.0,
                exhaust_outlet_temp_c=200.0,
                oil_name="Manual Oil",
                oil_mass_flow_kg_s=20.0,
                oil_inlet_temp_c=290.0,
                oil_outlet_temp_c=320.0,
                loop_mode=ThermalOilLoopMode.ADIABATIC_LINK,
                wf_name="Cyclopentane Screening",
                orc_heat_mode=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
                orc_power_mode=OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
            )
        )

        notes = build_operator_guidance(result)

        self.assertEqual(notes[0].severity, "critical")
        self.assertIn("sicaklik", notes[0].title.lower())
        self.assertIn("Egzoz cikis sicakligini yukseltin", notes[0].detail)

    def test_boiler_closure_warning_returns_warning_guidance(self) -> None:
        result = run_screening_case(
            ScreeningCaseInputs(
                case_name="warning-guidance",
                boiler_mode=BoilerMode.PERFORMANCE,
                exhaust_components=DEFAULT_EXHAUST_COMPOSITION,
                exhaust_mass_flow_kg_s=10.0,
                exhaust_inlet_temp_c=500.0,
                exhaust_outlet_temp_c=200.0,
                oil_name="Manual Oil",
                oil_mass_flow_kg_s=20.0,
                oil_inlet_temp_c=175.0,
                oil_outlet_temp_c=255.0,
                loop_mode=ThermalOilLoopMode.ADIABATIC_LINK,
                wf_name="Cyclopentane Screening",
                orc_heat_mode=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
                orc_power_mode=OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
                closure_tolerance_fraction=0.03,
            )
        )

        notes = build_operator_guidance(result)

        self.assertEqual(notes[0].severity, "warning")
        self.assertIn("enerji kapanisi", notes[0].title.lower())
        self.assertIn("Debi, sicaklik ve ozellik verilerinin ayni calisma anina ait oldugunu dogrulayin", notes[0].detail)

    def test_render_operator_guidance_returns_readable_text(self) -> None:
        result = run_screening_case(
            ScreeningCaseInputs(
                case_name="ok-guidance",
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
            )
        )

        text = render_operator_guidance(build_operator_guidance(result))

        self.assertIn("[INFO]", text)
        self.assertIn("brut elektrik gucu", text)


if __name__ == "__main__":
    unittest.main()
