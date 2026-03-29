from __future__ import annotations

from dataclasses import dataclass

from whrs_orc.domain.models import FluidLimitSpec, FluidSpec
from whrs_orc.properties.catalog import THERMAL_OIL_BY_NAME, find_thermal_oil_record


def _temp_c(temp_k: float) -> float:
    return temp_k - 273.15


def _temp_k(temp_c: float) -> float:
    return temp_c + 273.15


def _evaluate_linear_cp(cp_a: float, cp_b: float, temp_c: float) -> float:
    return cp_a + cp_b * temp_c


def _integrate(temp_start_k: float, temp_end_k: float, cp_function, *, segments: int = 32) -> float:
    if temp_start_k == temp_end_k:
        return 0.0
    step = (temp_end_k - temp_start_k) / segments
    total = 0.0
    for index in range(segments):
        t_1 = temp_start_k + index * step
        t_2 = t_1 + step
        total += 0.5 * (cp_function(t_1) + cp_function(t_2)) * (t_2 - t_1)
    return total


def _payload_float(payload: dict[str, float | int | str | bool], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


@dataclass(slots=True)
class PropertyResolution:
    value: float
    source: str


class ThermalOilPropertyProvider:
    def list_thermal_oils(self) -> list[dict[str, object]]:
        return list(THERMAL_OIL_BY_NAME.values())

    def metadata(self, fluid: FluidSpec) -> dict[str, object] | None:
        return find_thermal_oil_record(fluid.fluid_id) or find_thermal_oil_record(fluid.display_name)

    def density_kg_m3(self, fluid: FluidSpec) -> float | None:
        payload_density = _payload_float(fluid.property_model.payload, "density_kg_m3")
        if payload_density is not None:
            return payload_density
        record = self.metadata(fluid)
        if record is not None and record.get("density_kg_m3") is not None:
            return float(record["density_kg_m3"])
        return None

    def limits(self, fluid: FluidSpec) -> FluidLimitSpec | None:
        if fluid.limits is not None:
            return fluid.limits
        record = self.metadata(fluid)
        if record is None:
            return None
        return FluidLimitSpec(
            min_bulk_temp_k=_temp_k(float(record["t_min_c"])) if record.get("t_min_c") is not None else None,
            max_bulk_temp_k=_temp_k(float(record["max_bulk_temp_c"])) if record.get("max_bulk_temp_c") is not None else None,
        )

    def cp_j_kg_k(self, fluid: FluidSpec, temp_k: float) -> PropertyResolution:
        payload = fluid.property_model.payload
        cp_const = _payload_float(payload, "cp_const_j_kg_k")
        if cp_const is not None:
            return PropertyResolution(cp_const, "manual")

        cp_a = _payload_float(payload, "cp_a")
        cp_b = _payload_float(payload, "cp_b")
        if cp_a is not None and cp_b is not None:
            return PropertyResolution(_evaluate_linear_cp(cp_a, cp_b, _temp_c(temp_k)), "manual_correlation")

        record = self.metadata(fluid)
        if record is not None:
            return PropertyResolution(
                _evaluate_linear_cp(float(record["cp_a"]), float(record["cp_b"]), _temp_c(temp_k)),
                str(record.get("backend", "correlation")),
            )

        raise ValueError(f"Thermal oil properties are not available for `{fluid.display_name}`.")

    def heat_gain_j_kg(self, fluid: FluidSpec, inlet_temp_k: float, outlet_temp_k: float) -> PropertyResolution:
        value = _integrate(inlet_temp_k, outlet_temp_k, lambda temp_k: self.cp_j_kg_k(fluid, temp_k).value)
        cp_mid = self.cp_j_kg_k(fluid, 0.5 * (inlet_temp_k + outlet_temp_k))
        return PropertyResolution(value, cp_mid.source)

    def solve_outlet_temp_k(
        self,
        fluid: FluidSpec,
        inlet_temp_k: float,
        target_heat_gain_j_kg: float,
        *,
        upper_bound_temp_k: float | None = None,
        tolerance_j_kg: float = 1.0,
    ) -> tuple[float, float]:
        if target_heat_gain_j_kg <= 0.0:
            return inlet_temp_k, 0.0

        record_limits = self.limits(fluid)
        max_bulk_temp_k = upper_bound_temp_k or (record_limits.max_bulk_temp_k if record_limits is not None else None) or (inlet_temp_k + 400.0)
        lower = inlet_temp_k
        upper = max(max_bulk_temp_k, inlet_temp_k)
        achievable = self.heat_gain_j_kg(fluid, inlet_temp_k, upper).value
        if achievable <= target_heat_gain_j_kg:
            return upper, achievable

        for _ in range(80):
            mid = 0.5 * (lower + upper)
            heat_mid = self.heat_gain_j_kg(fluid, inlet_temp_k, mid).value
            if abs(heat_mid - target_heat_gain_j_kg) <= tolerance_j_kg:
                return mid, heat_mid
            if heat_mid < target_heat_gain_j_kg:
                lower = mid
            else:
                upper = mid

        mid = 0.5 * (lower + upper)
        return mid, self.heat_gain_j_kg(fluid, inlet_temp_k, mid).value

