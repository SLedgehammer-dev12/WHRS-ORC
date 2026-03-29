from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class CompositionBasis(StrEnum):
    MOLE_FRACTION = "mole_fraction"
    MASS_FRACTION = "mass_fraction"


class FluidKind(StrEnum):
    EXHAUST_GAS = "exhaust_gas"
    THERMAL_OIL = "thermal_oil"
    WORKING_FLUID = "working_fluid"
    COOLING_MEDIUM = "cooling_medium"
    UTILITY = "utility"


class PropertyBackend(StrEnum):
    AUTO = "auto"
    CANTERA = "cantera"
    COOLPROP = "coolprop"
    THERMO = "thermo"
    CHEMICALS = "chemicals"
    CORRELATION = "correlation"
    MANUAL = "manual"


@dataclass(slots=True)
class ComponentFraction:
    component_id: str
    fraction: float
    display_name: str | None = None
    source_reference: str | None = None


@dataclass(slots=True)
class CompositionSpec:
    basis: CompositionBasis = CompositionBasis.MOLE_FRACTION
    components: list[ComponentFraction] = field(default_factory=list)
    reference_state: str | None = None
    normalized: bool = False


@dataclass(slots=True)
class PropertyModelSpec:
    backend_id: PropertyBackend = PropertyBackend.AUTO
    model_id: str = "default"
    data_source: str | None = None
    data_version: str | None = None
    correlation_id: str | None = None
    allow_extrapolation: bool = False
    notes: str | None = None
    payload: dict[str, float | int | str | bool] = field(default_factory=dict)


@dataclass(slots=True)
class FluidLimitSpec:
    min_bulk_temp_k: float | None = None
    max_bulk_temp_k: float | None = None
    max_film_temp_k: float | None = None
    min_pressure_pa: float | None = None
    max_pressure_pa: float | None = None
    notes: str | None = None


@dataclass(slots=True)
class FluidSpec:
    fluid_id: str
    display_name: str
    kind: FluidKind
    property_model: PropertyModelSpec = field(default_factory=PropertyModelSpec)
    composition: CompositionSpec | None = None
    limits: FluidLimitSpec | None = None
    source_reference: str | None = None
    allow_manual_entry: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StatePoint:
    tag: str
    temp_k: float | None = None
    pressure_pa: float | None = None
    enthalpy_j_kg: float | None = None
    entropy_j_kg_k: float | None = None
    quality_mass: float | None = None
    density_kg_m3: float | None = None
    cp_j_kg_k: float | None = None
    phase_hint: str | None = None


@dataclass(slots=True)
class ProcessStream:
    stream_id: str
    display_name: str
    fluid: FluidSpec
    mass_flow_kg_s: float
    inlet: StatePoint
    outlet: StatePoint | None = None
    source_equipment_id: str | None = None
    target_equipment_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

