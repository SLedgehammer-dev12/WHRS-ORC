from __future__ import annotations

from math import hypot


def polyline_length(points: tuple[tuple[float, float], ...]) -> float:
    if len(points) < 2:
        return 0.0
    return sum(hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(points, points[1:]))


def point_along_polyline(points: tuple[tuple[float, float], ...], distance: float) -> tuple[float, float]:
    if not points:
        return (0.0, 0.0)
    if len(points) == 1:
        return points[0]

    total = polyline_length(points)
    if total <= 0.0:
        return points[0]
    target = distance % total
    traversed = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        segment = hypot(x2 - x1, y2 - y1)
        if segment <= 0.0:
            continue
        if traversed + segment >= target:
            fraction = (target - traversed) / segment
            return (x1 + (x2 - x1) * fraction, y1 + (y2 - y1) * fraction)
        traversed += segment
    return points[-1]


def points_from_segments(segments: tuple[tuple[float, float, float, float], ...]) -> tuple[tuple[float, float], ...]:
    if not segments:
        return ()
    points: list[tuple[float, float]] = []
    for index, (x1, y1, x2, y2) in enumerate(segments):
        if index == 0:
            points.append((x1, y1))
        points.append((x2, y2))
    return tuple(points)
