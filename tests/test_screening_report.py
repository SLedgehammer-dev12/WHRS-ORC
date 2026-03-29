from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.reporting.screening_report import (
    build_screening_markdown_report,
    build_screening_report_payload,
    default_report_filename,
)
from whrs_orc.solvers.screening_case import run_screening_case
from whrs_orc.ui.benchmark_cases import get_benchmark_case


class ScreeningReportTests(unittest.TestCase):
    def test_report_payload_is_json_serializable(self) -> None:
        benchmark = get_benchmark_case("balanced_performance")
        result = run_screening_case(benchmark.inputs)

        payload = build_screening_report_payload(benchmark.inputs, result)
        serialized = json.dumps(payload)

        self.assertIn("screening_case", serialized)
        self.assertIn("gross_electric_power_w", serialized)

    def test_markdown_report_contains_core_sections(self) -> None:
        benchmark = get_benchmark_case("design_efficiency_target")
        result = run_screening_case(benchmark.inputs)

        report = build_screening_markdown_report(benchmark.inputs, result)

        self.assertIn("# WHRS ORC Screening Report", report)
        self.assertIn("## KPI Summary", report)
        self.assertIn("## Operator Guidance", report)
        self.assertIn("### Boiler", report)

    def test_default_report_filename_slugifies_case_name(self) -> None:
        filename = default_report_filename("Benchmark - Balanced Performance", ".md")

        self.assertEqual(filename, "benchmark-balanced-performance.md")


if __name__ == "__main__":
    unittest.main()
