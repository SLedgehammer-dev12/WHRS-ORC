from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from whrs_orc.ui.stream_motion import point_along_polyline, points_from_segments, polyline_length


class StreamMotionTests(unittest.TestCase):
    def test_polyline_length_sums_segments(self) -> None:
        points = ((0.0, 0.0), (3.0, 4.0), (6.0, 4.0))

        self.assertAlmostEqual(polyline_length(points), 8.0)

    def test_point_along_polyline_interpolates_expected_location(self) -> None:
        points = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0))

        self.assertEqual(point_along_polyline(points, 5.0), (5.0, 0.0))
        self.assertEqual(point_along_polyline(points, 15.0), (10.0, 5.0))

    def test_points_from_segments_rebuilds_polyline_points(self) -> None:
        segments = ((0.0, 0.0, 4.0, 0.0), (4.0, 0.0, 4.0, 6.0))

        self.assertEqual(points_from_segments(segments), ((0.0, 0.0), (4.0, 0.0), (4.0, 6.0)))


if __name__ == "__main__":
    unittest.main()
