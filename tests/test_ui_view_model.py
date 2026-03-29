from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.equipment.contracts import BoilerDesignDriver, BoilerMode, OrcScreeningHeatMode, OrcScreeningPowerMode, ThermalOilLoopMode
from whrs_orc.ui.view_model import build_ui_behavior_state


class UiViewModelTests(unittest.TestCase):
    def test_performance_mode_disables_design_target_and_keeps_outlet_entries_open(self) -> None:
        state = build_ui_behavior_state(
            BoilerMode.PERFORMANCE,
            BoilerDesignDriver.TARGET_BOILER_EFFICIENCY,
            ThermalOilLoopMode.ADIABATIC_LINK,
            OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE,
            OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
            "Manual Oil",
            "Manual Working Fluid",
        )

        self.assertEqual(state.study_title, "Mevcut tesis analizi")
        self.assertFalse(state.design_target.enabled)
        self.assertTrue(state.exhaust_outlet_enabled)
        self.assertTrue(state.oil_outlet_enabled)
        self.assertFalse(state.loop_heat_loss_enabled)
        self.assertFalse(state.loop_target_delivery_enabled)
        self.assertFalse(state.orc_target_wf_outlet_enabled)
        self.assertFalse(state.orc_known_heat_input_enabled)
        self.assertTrue(state.orc_efficiency_enabled)
        self.assertFalse(state.gross_power_target_enabled)
        self.assertTrue(state.oil_manual_properties_enabled)
        self.assertTrue(state.wf_manual_properties_enabled)

    def test_design_mode_exposes_selected_driver_and_mode_specific_fields(self) -> None:
        state = build_ui_behavior_state(
            BoilerMode.DESIGN,
            BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE,
            ThermalOilLoopMode.TARGET_DELIVERY_TEMPERATURE,
            OrcScreeningHeatMode.KNOWN_ORC_HEAT_INPUT,
            OrcScreeningPowerMode.GROSS_EFFICIENCY_FROM_POWER,
            "Therminol VP-1",
            "Cyclopentane Screening",
        )

        self.assertEqual(state.study_title, "Tasarim calismasi")
        self.assertTrue(state.design_target.enabled)
        self.assertEqual(state.design_target.label, "Hedef yag cikis sicakligi")
        self.assertEqual(state.design_target.unit_hint, "degC")
        self.assertFalse(state.exhaust_outlet_enabled)
        self.assertFalse(state.oil_outlet_enabled)
        self.assertFalse(state.loop_heat_loss_enabled)
        self.assertTrue(state.loop_target_delivery_enabled)
        self.assertFalse(state.orc_target_wf_outlet_enabled)
        self.assertTrue(state.orc_known_heat_input_enabled)
        self.assertFalse(state.orc_efficiency_enabled)
        self.assertTrue(state.gross_power_target_enabled)
        self.assertFalse(state.oil_manual_properties_enabled)
        self.assertFalse(state.wf_manual_properties_enabled)


if __name__ == "__main__":
    unittest.main()
