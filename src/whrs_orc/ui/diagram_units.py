from __future__ import annotations

from dataclasses import dataclass

from whrs_orc.equipment.contracts import BoilerDesignDriver


@dataclass(frozen=True, slots=True)
class DiagramInputSpec:
    key: str
    label: str
    quantity: str
    default_unit: str
    base_state_key: str
    x: int
    y: int
    accent_color: str
    enable_attr: str | None = None


SUPPORTED_UNITS: dict[str, tuple[str, ...]] = {
    "temperature": ("degC", "K", "degF"),
    "pressure": ("Pa", "kPa", "bar"),
    "mass_flow": ("kg/s", "kg/h", "t/h"),
    "power": ("W", "kW", "MW"),
    "delta_t": ("K", "degC"),
    "ratio": ("frac", "%"),
    "conductance": ("W/K", "kW/K"),
}


PROCESS_INPUT_SPECS: tuple[DiagramInputSpec, ...] = (
    DiagramInputSpec("exhaust_mass_flow", "Exhaust flow", "mass_flow", "kg/s", "exhaust_mass_flow", 20, 20, "#de2f2f"),
    DiagramInputSpec("exhaust_inlet_temp", "Exhaust Tin", "temperature", "degC", "exhaust_inlet_temp", 20, 94, "#de2f2f"),
    DiagramInputSpec("exhaust_pressure", "Exhaust P", "pressure", "kPa", "exhaust_pressure", 20, 168, "#de2f2f"),
    DiagramInputSpec("exhaust_outlet_temp", "Stack Tout", "temperature", "degC", "exhaust_outlet_temp", 20, 242, "#de2f2f", "exhaust_outlet_enabled"),
    DiagramInputSpec("stack_min_temp", "Min stack", "temperature", "degC", "stack_min_temp", 20, 316, "#de2f2f"),
    DiagramInputSpec("oil_mass_flow", "Oil flow", "mass_flow", "kg/s", "oil_mass_flow", 352, 16, "#6a39a8"),
    DiagramInputSpec("wf_max_outlet_temp", "WF Tmax", "temperature", "degC", "wf_max_outlet_temp", 662, 16, "#f1b400"),
    DiagramInputSpec("eta_orc_gross", "Gross eta", "ratio", "%", "eta_orc_gross", 1260, 20, "#134f95", "orc_efficiency_enabled"),
    DiagramInputSpec("gross_power_target", "Pgross target", "power", "kW", "gross_power_target", 1260, 96, "#134f95", "gross_power_target_enabled"),
    DiagramInputSpec("closure_tolerance", "Closure tol", "ratio", "%", "closure_tolerance", 1260, 172, "#134f95"),
    DiagramInputSpec("oil_outlet_temp", "Boiler oil out", "temperature", "degC", "oil_outlet_temp", 344, 560, "#6a39a8", "oil_outlet_enabled"),
    DiagramInputSpec("oil_inlet_temp", "Oil return", "temperature", "degC", "oil_inlet_temp", 344, 636, "#6a39a8"),
    DiagramInputSpec("loop_target_delivery_temp", "Oil to ORC", "temperature", "degC", "loop_target_delivery_temp", 520, 560, "#6a39a8", "loop_target_delivery_enabled"),
    DiagramInputSpec("loop_heat_loss", "Loop loss", "power", "kW", "loop_heat_loss", 520, 636, "#6a39a8", "loop_heat_loss_enabled"),
    DiagramInputSpec("orc_min_approach", "Min approach", "delta_t", "K", "orc_min_approach", 726, 560, "#f1b400"),
    DiagramInputSpec("wf_inlet_temp", "WF Tin", "temperature", "degC", "wf_inlet_temp", 726, 636, "#f1b400"),
    DiagramInputSpec("orc_target_wf_outlet", "WF Tout target", "temperature", "degC", "orc_target_wf_outlet", 934, 560, "#f1b400", "orc_target_wf_outlet_enabled"),
    DiagramInputSpec("orc_known_heat_input", "ORC Qin", "power", "kW", "orc_known_heat_input", 934, 636, "#f1b400", "orc_known_heat_input_enabled"),
)


def supported_units(quantity: str) -> tuple[str, ...]:
    if quantity not in SUPPORTED_UNITS:
        raise KeyError(f"Unsupported quantity `{quantity}`.")
    return SUPPORTED_UNITS[quantity]


def convert_to_base(quantity: str, value: float, unit: str) -> float:
    if quantity == "temperature":
        if unit == "degC":
            return value
        if unit == "K":
            return value - 273.15
        if unit == "degF":
            return (value - 32.0) * 5.0 / 9.0
    elif quantity == "pressure":
        if unit == "Pa":
            return value
        if unit == "kPa":
            return value * 1_000.0
        if unit == "bar":
            return value * 100_000.0
    elif quantity == "mass_flow":
        if unit == "kg/s":
            return value
        if unit == "kg/h":
            return value / 3_600.0
        if unit == "t/h":
            return value * 1_000.0 / 3_600.0
    elif quantity == "power":
        if unit == "W":
            return value
        if unit == "kW":
            return value * 1_000.0
        if unit == "MW":
            return value * 1_000_000.0
    elif quantity == "delta_t":
        if unit in {"K", "degC"}:
            return value
    elif quantity == "ratio":
        if unit == "frac":
            return value
        if unit == "%":
            return value / 100.0
    elif quantity == "conductance":
        if unit == "W/K":
            return value
        if unit == "kW/K":
            return value * 1_000.0
    raise ValueError(f"Unsupported unit `{unit}` for quantity `{quantity}`.")


def convert_from_base(quantity: str, value: float, unit: str) -> float:
    if quantity == "temperature":
        if unit == "degC":
            return value
        if unit == "K":
            return value + 273.15
        if unit == "degF":
            return value * 9.0 / 5.0 + 32.0
    elif quantity == "pressure":
        if unit == "Pa":
            return value
        if unit == "kPa":
            return value / 1_000.0
        if unit == "bar":
            return value / 100_000.0
    elif quantity == "mass_flow":
        if unit == "kg/s":
            return value
        if unit == "kg/h":
            return value * 3_600.0
        if unit == "t/h":
            return value * 3_600.0 / 1_000.0
    elif quantity == "power":
        if unit == "W":
            return value
        if unit == "kW":
            return value / 1_000.0
        if unit == "MW":
            return value / 1_000_000.0
    elif quantity == "delta_t":
        if unit in {"K", "degC"}:
            return value
    elif quantity == "ratio":
        if unit == "frac":
            return value
        if unit == "%":
            return value * 100.0
    elif quantity == "conductance":
        if unit == "W/K":
            return value
        if unit == "kW/K":
            return value / 1_000.0
    raise ValueError(f"Unsupported unit `{unit}` for quantity `{quantity}`.")


def format_for_display(quantity: str, value: float) -> str:
    decimals = {
        "temperature": 1,
        "pressure": 3,
        "mass_flow": 3,
        "power": 3,
        "delta_t": 2,
        "ratio": 3,
        "conductance": 3,
    }
    digits = decimals.get(quantity, 3)
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return text if text else "0"


def design_target_quantity(driver: BoilerDesignDriver) -> str:
    if driver in {BoilerDesignDriver.MINIMUM_STACK_TEMPERATURE, BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE}:
        return "temperature"
    if driver in {BoilerDesignDriver.TARGET_BOILER_EFFICIENCY, BoilerDesignDriver.TARGET_EFFECTIVENESS}:
        return "ratio"
    if driver is BoilerDesignDriver.TARGET_TRANSFERRED_POWER:
        return "power"
    if driver is BoilerDesignDriver.TARGET_UA:
        return "conductance"
    if driver is BoilerDesignDriver.MINIMUM_PINCH_APPROACH:
        return "delta_t"
    raise KeyError(f"Unsupported driver `{driver}`.")


def design_target_default_unit(driver: BoilerDesignDriver) -> str:
    mapping = {
        BoilerDesignDriver.MINIMUM_STACK_TEMPERATURE: "degC",
        BoilerDesignDriver.TARGET_BOILER_EFFICIENCY: "frac",
        BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE: "degC",
        BoilerDesignDriver.TARGET_TRANSFERRED_POWER: "kW",
        BoilerDesignDriver.TARGET_EFFECTIVENESS: "frac",
        BoilerDesignDriver.TARGET_UA: "kW/K",
        BoilerDesignDriver.MINIMUM_PINCH_APPROACH: "K",
    }
    return mapping[driver]


def design_target_default_value(driver: BoilerDesignDriver) -> float:
    mapping = {
        BoilerDesignDriver.MINIMUM_STACK_TEMPERATURE: 150.0,
        BoilerDesignDriver.TARGET_BOILER_EFFICIENCY: 0.5,
        BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE: 250.0,
        BoilerDesignDriver.TARGET_TRANSFERRED_POWER: 1_000_000.0,
        BoilerDesignDriver.TARGET_EFFECTIVENESS: 0.7,
        BoilerDesignDriver.TARGET_UA: 5_000.0,
        BoilerDesignDriver.MINIMUM_PINCH_APPROACH: 5.0,
    }
    return mapping[driver]
