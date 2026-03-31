from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.logging.run_logger import build_screening_run_log_record, log_screening_case_run
from whrs_orc.solvers.screening_case import run_screening_case
from whrs_orc.ui.benchmark_cases import get_benchmark_case


class RunLoggerTests(unittest.TestCase):
    def test_build_screening_run_log_record_includes_status_summary(self) -> None:
        benchmark = get_benchmark_case("balanced_performance")
        result = run_screening_case(benchmark.inputs)

        record = build_screening_run_log_record(benchmark.inputs, result)

        self.assertEqual(record["event_type"], "screening_case_solved")
        self.assertEqual(record["case_name"], benchmark.inputs.case_name)
        self.assertFalse(record["blocked"])
        self.assertEqual(record["statuses"]["boiler"], "success")

    def test_log_screening_case_run_appends_jsonl_record(self) -> None:
        benchmark = get_benchmark_case("balanced_performance")
        result = run_screening_case(benchmark.inputs)

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "screening_runs.jsonl"
            log_screening_case_run(log_path, benchmark.inputs, result)
            lines = log_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["case_name"], benchmark.inputs.case_name)
        self.assertIn("gross_electric_power_w", payload["kpis"])


if __name__ == "__main__":
    unittest.main()
