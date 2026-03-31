from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.ui.stream_palette import color_for_temperature, colors_for_temperature_span, fluid_gradient, gradient_swatch_colors


class StreamPaletteTests(unittest.TestCase):
    def test_each_fluid_palette_has_distinct_hot_color(self) -> None:
        self.assertNotEqual(fluid_gradient("exhaust").hot_color, fluid_gradient("oil").hot_color)
        self.assertNotEqual(fluid_gradient("oil").hot_color, fluid_gradient("working_fluid").hot_color)

    def test_hotter_temperature_returns_different_color_from_colder_temperature(self) -> None:
        cold = color_for_temperature("exhaust", 180.0)
        hot = color_for_temperature("exhaust", 520.0)

        self.assertNotEqual(cold, hot)

    def test_temperature_span_returns_requested_number_of_colors(self) -> None:
        colors = colors_for_temperature_span("oil", 170.0, 300.0, steps=5)

        self.assertEqual(len(colors), 5)
        self.assertNotEqual(colors[0], colors[-1])

    def test_gradient_swatch_colors_support_legend_generation(self) -> None:
        swatch = gradient_swatch_colors("working_fluid", steps=4)

        self.assertEqual(len(swatch), 4)
        self.assertNotEqual(swatch[0], swatch[-1])


if __name__ == "__main__":
    unittest.main()
