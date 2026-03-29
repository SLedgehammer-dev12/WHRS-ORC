from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.solvers.screening_case import run_screening_case
from whrs_orc.ui.benchmark_cases import get_benchmark_case, list_benchmark_cases


class BenchmarkCaseTests(unittest.TestCase):
    def test_benchmark_library_exposes_three_cases(self) -> None:
        cases = list_benchmark_cases()

        self.assertGreaterEqual(len(cases), 3)
        self.assertEqual(cases[0].key, "balanced_performance")

    def test_benchmark_cases_run_without_blocking_the_screening_chain(self) -> None:
        for definition in list_benchmark_cases():
            with self.subTest(case=definition.key):
                result = run_screening_case(definition.inputs)
                self.assertFalse(result.boiler_result.blocked_state.blocked)
                self.assertIsNotNone(result.orc_power_result)
                self.assertFalse(result.orc_power_result.blocked_state.blocked)

    def test_get_benchmark_case_returns_requested_case(self) -> None:
        case = get_benchmark_case("design_efficiency_target")

        self.assertEqual(case.display_name, "Design Efficiency Target")
        self.assertEqual(case.inputs.case_name, "Benchmark - Design Efficiency Target")


if __name__ == "__main__":
    unittest.main()
