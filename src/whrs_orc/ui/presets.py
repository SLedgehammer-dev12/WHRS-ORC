from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkingFluidPreset:
    name: str
    cp_const_j_kg_k: float
    max_outlet_temp_c: float


DEFAULT_EXHAUST_COMPOSITION: list[tuple[str, float]] = [
    ("N2", 0.74),
    ("O2", 0.10),
    ("CO2", 0.06),
    ("H2O", 0.10),
]


WORKING_FLUID_PRESETS: dict[str, WorkingFluidPreset] = {
    "Cyclopentane Screening": WorkingFluidPreset("Cyclopentane Screening", 2000.0, 170.0),
    "Isopentane Screening": WorkingFluidPreset("Isopentane Screening", 2150.0, 165.0),
    "n-Pentane Screening": WorkingFluidPreset("n-Pentane Screening", 2250.0, 155.0),
    "Manual Working Fluid": WorkingFluidPreset("Manual Working Fluid", 2000.0, 170.0),
}

