from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.persistence.saved_cases import default_saved_case_filename, read_saved_case, write_saved_case
from whrs_orc.solvers.screening_case import OrcHeaterStageInput
from whrs_orc.ui.benchmark_cases import get_benchmark_case


class SavedCaseTests(unittest.TestCase):
    def test_saved_case_roundtrip_preserves_case_inputs(self) -> None:
        benchmark = copy.deepcopy(get_benchmark_case("design_efficiency_target"))

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "design-case.whrs.json"
            write_saved_case(
                target_path,
                benchmark.inputs,
                source_label=benchmark.display_name,
                note=benchmark.summary,
            )
            loaded = read_saved_case(target_path)

        self.assertEqual(loaded.case_inputs.case_name, benchmark.inputs.case_name)
        self.assertEqual(loaded.case_inputs.boiler_mode, benchmark.inputs.boiler_mode)
        self.assertEqual(loaded.case_inputs.boiler_design_driver, benchmark.inputs.boiler_design_driver)
        self.assertEqual(loaded.source_label, benchmark.display_name)
        self.assertEqual(loaded.note, benchmark.summary)

    def test_default_saved_case_filename_slugifies_case_name(self) -> None:
        filename = default_saved_case_filename("Benchmark - Balanced Performance")

        self.assertEqual(filename, "benchmark-balanced-performance.whrs.json")

    def test_saved_case_roundtrip_preserves_orc_heater_stage_inputs(self) -> None:
        benchmark = copy.deepcopy(get_benchmark_case("balanced_performance"))
        benchmark.inputs.orc_heater_stage_count = 2
        benchmark.inputs.orc_heater_stages = [
            OrcHeaterStageInput(stage_name="Preheater", target_wf_outlet_temp_c=130.0),
            OrcHeaterStageInput(stage_name="Vaporizer", target_wf_outlet_temp_c=150.0),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "multistage-case.whrs.json"
            write_saved_case(target_path, benchmark.inputs)
            loaded = read_saved_case(target_path)

        self.assertEqual(loaded.case_inputs.orc_heater_stage_count, 2)
        self.assertEqual(len(loaded.case_inputs.orc_heater_stages), 2)
        self.assertEqual(loaded.case_inputs.orc_heater_stages[0].stage_name, "Preheater")


if __name__ == "__main__":
    unittest.main()
