from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.equipment.contracts import BoilerDesignDriver
from whrs_orc.ui.diagram_units import (
    convert_from_base,
    convert_to_base,
    design_target_default_unit,
    design_target_default_value,
    design_target_quantity,
    format_for_display,
    supported_units,
)


class DiagramUnitsTests(unittest.TestCase):
    def test_temperature_round_trip_with_fahrenheit(self) -> None:
        base_c = convert_to_base("temperature", 392.0, "degF")
        self.assertAlmostEqual(base_c, 200.0, places=6)
        self.assertAlmostEqual(convert_from_base("temperature", base_c, "K"), 473.15, places=6)

    def test_mass_flow_and_power_unit_conversions(self) -> None:
        self.assertAlmostEqual(convert_to_base("mass_flow", 36_000.0, "kg/h"), 10.0, places=6)
        self.assertAlmostEqual(convert_from_base("power", 1_500_000.0, "MW"), 1.5, places=6)

    def test_ratio_percent_conversion(self) -> None:
        self.assertAlmostEqual(convert_to_base("ratio", 18.0, "%"), 0.18, places=6)
        self.assertAlmostEqual(convert_from_base("ratio", 0.18, "%"), 18.0, places=6)

    def test_supported_units_and_formatting(self) -> None:
        self.assertEqual(supported_units("pressure"), ("Pa", "kPa", "bar"))
        self.assertEqual(format_for_display("mass_flow", 10.0), "10")
        self.assertEqual(format_for_display("temperature", 175.25), "175.2")

    def test_design_target_driver_mapping(self) -> None:
        self.assertEqual(design_target_quantity(BoilerDesignDriver.TARGET_UA), "conductance")
        self.assertEqual(design_target_default_unit(BoilerDesignDriver.TARGET_TRANSFERRED_POWER), "kW")
        self.assertEqual(design_target_default_value(BoilerDesignDriver.MINIMUM_PINCH_APPROACH), 5.0)
        self.assertAlmostEqual(convert_to_base("conductance", 2.5, "kW/K"), 2500.0, places=6)
        self.assertAlmostEqual(convert_from_base("conductance", 2500.0, "kW/K"), 2.5, places=6)


if __name__ == "__main__":
    unittest.main()
