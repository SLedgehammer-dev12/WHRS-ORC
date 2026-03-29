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
from whrs_orc.ui.presets import DEFAULT_EXHAUST_COMPOSITION
from whrs_orc.ui.process_diagram import build_empty_process_snapshot, build_process_snapshot, status_color


class ProcessDiagramTests(unittest.TestCase):
    def test_empty_snapshot_is_idle(self) -> None:
        snapshot = build_empty_process_snapshot()

        self.assertEqual(snapshot.factory.status, "idle")
        self.assertIn("Awaiting solve", snapshot.boiler.secondary_text)

    def test_snapshot_maps_successful_case_to_process_labels(self) -> None:
        result = run_screening_case(
            ScreeningCaseInputs(
                case_name="diagram-case",
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

        snapshot = build_process_snapshot(result)

        self.assertEqual(snapshot.boiler.status, "success")
        self.assertIn("Q ", snapshot.boiler.primary_text)
        self.assertIn("eta ", snapshot.generator.secondary_text)
        self.assertIn("Gross electric output", snapshot.headline)
        self.assertEqual(status_color(snapshot.generator.status), "#2e8b57")


if __name__ == "__main__":
    unittest.main()
