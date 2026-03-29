from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.domain.result_schema import MetricValue, ResultEnvelope, ResultStatus


class ResultSchemaTests(unittest.TestCase):
    def test_metric_can_be_added_to_result(self) -> None:
        result = ResultEnvelope(
            result_id="result-1",
            model_name="unit_test",
            model_version="0.1.0",
            status=ResultStatus.SUCCESS,
        )

        result.add_metric(MetricValue("q_test_w", "Test Heat", 123.0, "W"))

        self.assertIn("q_test_w", result.values)
        self.assertEqual(result.values["q_test_w"].value_si, 123.0)

    def test_blocked_result_has_required_state(self) -> None:
        result = ResultEnvelope.blocked_result(
            result_id="blocked-1",
            model_name="unit_test",
            model_version="0.1.0",
            code="VAL-001",
            reason="Blocked for test.",
            source="unit_test",
        )

        self.assertEqual(result.status, ResultStatus.BLOCKED)
        self.assertTrue(result.blocked_state.blocked)
        self.assertEqual(result.blocked_state.code, "VAL-001")


if __name__ == "__main__":
    unittest.main()

