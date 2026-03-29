from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from whrs_orc.domain.models import FluidSpec, PropertyBackend


def _temp_c(temp_k: float) -> float:
    return temp_k - 273.15


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


class WorkingFluidScreeningProvider:
    def cp_j_kg_k(self, fluid: FluidSpec, temp_k: float, pressure_pa: float | None = None) -> PropertyResolution:
        payload = fluid.property_model.payload
        cp_const = _payload_float(payload, "cp_const_j_kg_k")
        if cp_const is not None:
            return PropertyResolution(cp_const, "manual")

        cp_a = _payload_float(payload, "cp_a")
        cp_b = _payload_float(payload, "cp_b")
        if cp_a is not None and cp_b is not None:
            return PropertyResolution(_evaluate_linear_cp(cp_a, cp_b, _temp_c(temp_k)), "manual_correlation")

        if fluid.property_model.backend_id is PropertyBackend.COOLPROP:
            try:
                return PropertyResolution(self._coolprop_cp(fluid, temp_k, pressure_pa or 101_325.0), "coolprop")
            except Exception as exc:
                raise ValueError(f"CoolProp screening property lookup failed for `{fluid.display_name}`: {exc}") from exc

        raise ValueError(
            f"Working-fluid screening properties are not available for `{fluid.display_name}`. "
            "Provide manual cp data or use a supported backend."
        )

    def heat_gain_j_kg(self, fluid: FluidSpec, inlet_temp_k: float, outlet_temp_k: float, pressure_pa: float | None = None) -> PropertyResolution:
        value = _integrate(inlet_temp_k, outlet_temp_k, lambda temp_k: self.cp_j_kg_k(fluid, temp_k, pressure_pa).value)
        cp_mid = self.cp_j_kg_k(fluid, 0.5 * (inlet_temp_k + outlet_temp_k), pressure_pa)
        return PropertyResolution(value, cp_mid.source)

    def solve_outlet_temp_k(
        self,
        fluid: FluidSpec,
        inlet_temp_k: float,
        target_heat_gain_j_kg: float,
        *,
        pressure_pa: float | None = None,
        upper_bound_temp_k: float | None = None,
        tolerance_j_kg: float = 1.0,
    ) -> tuple[float, float]:
        if target_heat_gain_j_kg <= 0.0:
            return inlet_temp_k, 0.0

        max_temp_k = upper_bound_temp_k or (fluid.limits.max_bulk_temp_k if fluid.limits is not None else None) or (inlet_temp_k + 300.0)
        lower = inlet_temp_k
        upper = max(max_temp_k, inlet_temp_k)
        achievable = self.heat_gain_j_kg(fluid, inlet_temp_k, upper, pressure_pa).value
        if achievable <= target_heat_gain_j_kg:
            return upper, achievable

        for _ in range(80):
            mid = 0.5 * (lower + upper)
            heat_mid = self.heat_gain_j_kg(fluid, inlet_temp_k, mid, pressure_pa).value
            if abs(heat_mid - target_heat_gain_j_kg) <= tolerance_j_kg:
                return mid, heat_mid
            if heat_mid < target_heat_gain_j_kg:
                lower = mid
            else:
                upper = mid

        mid = 0.5 * (lower + upper)
        return mid, self.heat_gain_j_kg(fluid, inlet_temp_k, mid, pressure_pa).value

    @staticmethod
    @lru_cache(maxsize=1)
    def _coolprop_props():
        from CoolProp.CoolProp import PropsSI  # type: ignore

        return PropsSI

    def _coolprop_cp(self, fluid: FluidSpec, temp_k: float, pressure_pa: float) -> float:
        fluid_name = str(fluid.metadata.get("coolprop_name") or fluid.fluid_id)
        props = self._coolprop_props()
        return float(props("C", "T", temp_k, "P", pressure_pa, fluid_name))

