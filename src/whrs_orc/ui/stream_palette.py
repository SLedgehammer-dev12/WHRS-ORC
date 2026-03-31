from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FluidGradient:
    fluid_key: str
    label: str
    cold_color: str
    hot_color: str
    reference_min_temp_c: float
    reference_max_temp_c: float


_FLUID_GRADIENTS: dict[str, FluidGradient] = {
    "exhaust": FluidGradient(
        fluid_key="exhaust",
        label="Exhaust gas",
        cold_color="#f3c688",
        hot_color="#c92228",
        reference_min_temp_c=100.0,
        reference_max_temp_c=650.0,
    ),
    "oil": FluidGradient(
        fluid_key="oil",
        label="Thermal oil",
        cold_color="#d8c8ff",
        hot_color="#6128b5",
        reference_min_temp_c=120.0,
        reference_max_temp_c=360.0,
    ),
    "working_fluid": FluidGradient(
        fluid_key="working_fluid",
        label="Organic fluid",
        cold_color="#9feaf0",
        hot_color="#d8a315",
        reference_min_temp_c=40.0,
        reference_max_temp_c=220.0,
    ),
    "power": FluidGradient(
        fluid_key="power",
        label="Electrical path",
        cold_color="#89b6ff",
        hot_color="#0f4f9f",
        reference_min_temp_c=0.0,
        reference_max_temp_c=1.0,
    ),
}


def fluid_gradient(fluid_key: str) -> FluidGradient:
    if fluid_key not in _FLUID_GRADIENTS:
        raise KeyError(f"Unsupported fluid palette `{fluid_key}`.")
    return _FLUID_GRADIENTS[fluid_key]


def gradient_swatch_colors(fluid_key: str, *, steps: int = 6) -> tuple[str, ...]:
    return colors_for_temperature_span(fluid_key, 0.0, 1.0, steps=steps, normalized=True)


def color_for_temperature(fluid_key: str, temp_c: float) -> str:
    palette = fluid_gradient(fluid_key)
    position = _clamp01((temp_c - palette.reference_min_temp_c) / max(palette.reference_max_temp_c - palette.reference_min_temp_c, 1.0))
    return blend_hex(palette.cold_color, palette.hot_color, position)


def colors_for_temperature_span(
    fluid_key: str,
    start_temp_c: float,
    end_temp_c: float,
    *,
    steps: int,
    normalized: bool = False,
) -> tuple[str, ...]:
    if steps <= 0:
        raise ValueError("`steps` must be at least 1.")
    palette = fluid_gradient(fluid_key)
    if normalized:
        start_pos = _clamp01(start_temp_c)
        end_pos = _clamp01(end_temp_c)
    else:
        denominator = max(palette.reference_max_temp_c - palette.reference_min_temp_c, 1.0)
        start_pos = _clamp01((start_temp_c - palette.reference_min_temp_c) / denominator)
        end_pos = _clamp01((end_temp_c - palette.reference_min_temp_c) / denominator)
    if steps == 1:
        return (blend_hex(palette.cold_color, palette.hot_color, (start_pos + end_pos) / 2.0),)
    colors: list[str] = []
    for index in range(steps):
        fraction = index / (steps - 1)
        position = start_pos + (end_pos - start_pos) * fraction
        colors.append(blend_hex(palette.cold_color, palette.hot_color, position))
    return tuple(colors)


def blend_hex(color_a: str, color_b: str, fraction: float) -> str:
    red_a, green_a, blue_a = _hex_to_rgb(color_a)
    red_b, green_b, blue_b = _hex_to_rgb(color_b)
    clamped = _clamp01(fraction)
    return _rgb_to_hex(
        round(red_a + (red_b - red_a) * clamped),
        round(green_a + (green_b - green_a) * clamped),
        round(blue_a + (blue_b - blue_a) * clamped),
    )


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    cleaned = value.lstrip("#")
    if len(cleaned) != 6:
        raise ValueError(f"Color `{value}` must be in #RRGGBB format.")
    return int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16)


def _rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
