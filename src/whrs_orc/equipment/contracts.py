from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from whrs_orc.domain.models import ProcessStream


class ExhaustSourceMode(StrEnum):
    AVAILABLE_HEAT_FROM_STACK_LIMIT = "available_heat_from_stack_limit"
    RELEASED_HEAT_FROM_OUTLET_TEMPERATURE = "released_heat_from_outlet_temperature"


class BoilerMode(StrEnum):
    PERFORMANCE = "performance"
    DESIGN = "design"


class BoilerDesignDriver(StrEnum):
    MINIMUM_STACK_TEMPERATURE = "minimum_stack_temperature"
    TARGET_BOILER_EFFICIENCY = "target_boiler_efficiency"
    TARGET_OIL_OUTLET_TEMPERATURE = "target_oil_outlet_temperature"
    TARGET_TRANSFERRED_POWER = "target_transferred_power"
    TARGET_EFFECTIVENESS = "target_effectiveness"
    TARGET_UA = "target_ua"
    MINIMUM_PINCH_APPROACH = "minimum_pinch_approach"


class ThermalOilLoopMode(StrEnum):
    ADIABATIC_LINK = "adiabatic_link"
    RATED_HEAT_LOSS = "rated_heat_loss"
    TARGET_DELIVERY_TEMPERATURE = "target_delivery_temperature"


class OrcScreeningHeatMode(StrEnum):
    SCREENING_FROM_OIL_SIDE = "screening_from_oil_side"
    SINGLE_PHASE_TEMPERATURE_GAIN = "single_phase_temperature_gain"
    KNOWN_ORC_HEAT_INPUT = "known_orc_heat_input"


class OrcScreeningPowerMode(StrEnum):
    GROSS_POWER_FROM_EFFICIENCY = "gross_power_from_efficiency"
    GROSS_EFFICIENCY_FROM_POWER = "gross_efficiency_from_power"


@dataclass(slots=True)
class ExhaustSourceConstraints:
    stack_min_temp_k: float | None = None


@dataclass(slots=True)
class ExhaustSourceRequest:
    equipment_id: str
    mode: ExhaustSourceMode
    exhaust_stream: ProcessStream
    constraints: ExhaustSourceConstraints = field(default_factory=ExhaustSourceConstraints)
    case_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BoilerConstraints:
    stack_min_temp_k: float | None = None
    min_pinch_delta_t_k: float | None = None
    max_closure_fraction: float = 0.03
    max_oil_bulk_temp_k: float | None = None


@dataclass(slots=True)
class BoilerDesignTarget:
    design_driver: BoilerDesignDriver
    target_value_si: float
    target_unit_si: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WasteHeatBoilerRequest:
    equipment_id: str
    mode: BoilerMode
    exhaust_stream: ProcessStream
    oil_stream: ProcessStream
    constraints: BoilerConstraints = field(default_factory=BoilerConstraints)
    design_target: BoilerDesignTarget | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    case_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ThermalOilLoopConstraints:
    max_oil_bulk_temp_k: float | None = None


@dataclass(slots=True)
class ThermalOilLoopRequest:
    equipment_id: str
    mode: ThermalOilLoopMode
    oil_supply_stream: ProcessStream
    oil_return_stream: ProcessStream
    constraints: ThermalOilLoopConstraints = field(default_factory=ThermalOilLoopConstraints)
    parameters: dict[str, Any] = field(default_factory=dict)
    case_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrcScreeningHeatConstraints:
    min_approach_delta_t_k: float | None = None
    max_wf_outlet_temp_k: float | None = None


@dataclass(slots=True)
class OrcHeaterStageTarget:
    stage_name: str
    duty_fraction: float | None = None
    target_wf_outlet_temp_k: float | None = None
    heat_input_w: float | None = None


@dataclass(slots=True)
class OrcScreeningHeatRequest:
    equipment_id: str
    mode: OrcScreeningHeatMode
    oil_hot_stream: ProcessStream
    wf_cold_stream: ProcessStream
    heater_stages: list[OrcHeaterStageTarget] = field(default_factory=list)
    constraints: OrcScreeningHeatConstraints = field(default_factory=OrcScreeningHeatConstraints)
    parameters: dict[str, Any] = field(default_factory=dict)
    case_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrcScreeningPowerRequest:
    equipment_id: str
    mode: OrcScreeningPowerMode
    q_orc_absorbed_w: float
    eta_orc_gross_target: float | None = None
    gross_electric_power_target_w: float | None = None
    q_exhaust_available_w: float | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    case_context: dict[str, Any] = field(default_factory=dict)
