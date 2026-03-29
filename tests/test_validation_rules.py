from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.domain.models import (
    ComponentFraction,
    CompositionSpec,
    FluidKind,
    FluidSpec,
    ProcessStream,
    PropertyModelSpec,
    StatePoint,
)
from whrs_orc.solvers.validation_rules import (
    validate_composition_sum,
    validate_minimum_temperature_approach,
    validate_positive_mass_flow,
    validate_single_design_driver,
)


class ValidationRuleTests(unittest.TestCase):
    def test_composition_sum_must_equal_one(self) -> None:
        stream = ProcessStream(
            stream_id="exhaust",
            display_name="Exhaust",
            fluid=FluidSpec(
                fluid_id="exhaust",
                display_name="Exhaust",
                kind=FluidKind.EXHAUST_GAS,
                property_model=PropertyModelSpec(),
                composition=CompositionSpec(
                    components=[
                        ComponentFraction("N2", 0.7),
                        ComponentFraction("O2", 0.1),
                    ]
                ),
            ),
            mass_flow_kg_s=1.0,
            inlet=StatePoint(tag="in", temp_k=500.0),
        )

        issues = validate_composition_sum(stream)

        self.assertTrue(issues)
        self.assertEqual(issues[0].code, "VAL-COMP-001")

    def test_mass_flow_must_be_positive(self) -> None:
        stream = ProcessStream(
            stream_id="oil",
            display_name="Oil",
            fluid=FluidSpec(fluid_id="oil", display_name="Oil", kind=FluidKind.THERMAL_OIL),
            mass_flow_kg_s=0.0,
            inlet=StatePoint(tag="in", temp_k=400.0),
        )

        issues = validate_positive_mass_flow(stream)

        self.assertTrue(issues)
        self.assertEqual(issues[0].code, "VAL-FLOW-001")

    def test_design_driver_count_must_be_one(self) -> None:
        issues = validate_single_design_driver(0)

        self.assertTrue(issues)
        self.assertEqual(issues[0].code, "VAL-BOILER-003")

    def test_negative_temperature_approach_blocks(self) -> None:
        issues = validate_minimum_temperature_approach(-2.0, minimum_delta_t_k=0.0, source="boiler")

        self.assertTrue(issues)
        self.assertEqual(issues[0].code, "VAL-HX-003")


if __name__ == "__main__":
    unittest.main()
