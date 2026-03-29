from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from whrs_orc.domain.models import CompositionBasis, FluidSpec, PropertyBackend
from whrs_orc.properties.catalog import EXHAUST_COMPONENT_LIBRARY, backend_status


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


class ExhaustPropertyProvider:
    def cp_j_kg_k(self, fluid: FluidSpec, temp_k: float, pressure_pa: float | None = None) -> PropertyResolution:
        payload = fluid.property_model.payload
        cp_const = _payload_float(payload, "cp_const_j_kg_k")
        if cp_const is not None:
            return PropertyResolution(cp_const, "manual")

        cp_a = _payload_float(payload, "cp_a")
        cp_b = _payload_float(payload, "cp_b")
        if cp_a is not None and cp_b is not None:
            return PropertyResolution(_evaluate_linear_cp(cp_a, cp_b, _temp_c(temp_k)), "manual_correlation")

        if fluid.composition is None or not fluid.composition.components:
            raise ValueError(f"Exhaust composition is not defined for `{fluid.display_name}`.")
        if fluid.composition.basis is not CompositionBasis.MOLE_FRACTION:
            raise ValueError("Only mole-fraction exhaust composition is supported in the first implementation pass.")

        pressure_pa = pressure_pa or 101_325.0
        total_fraction = sum(component.fraction for component in fluid.composition.components)
        if total_fraction <= 0.0:
            raise ValueError("Exhaust composition total fraction must be positive.")

        cp_molar_like = 0.0
        mixture_mw = 0.0
        sources: set[str] = set()
        for component_fraction in fluid.composition.components:
            component = EXHAUST_COMPONENT_LIBRARY.get(component_fraction.component_id)
            if component is None:
                raise ValueError(f"Unsupported exhaust component `{component_fraction.component_id}`.")
            cp_component, source = self._pure_component_cp_j_kg_k(
                component=component,
                temp_k=temp_k,
                pressure_pa=pressure_pa,
                backend=fluid.property_model.backend_id,
            )
            fraction = component_fraction.fraction / total_fraction
            mw = float(component["mw"])
            cp_molar_like += fraction * mw * cp_component
            mixture_mw += fraction * mw
            sources.add(source)

        return PropertyResolution(cp_molar_like / mixture_mw, sources.pop() if len(sources) == 1 else "hybrid")

    def heat_release_j_kg(
        self,
        fluid: FluidSpec,
        inlet_temp_k: float,
        outlet_temp_k: float,
        pressure_pa: float | None = None,
    ) -> PropertyResolution:
        value = _integrate(outlet_temp_k, inlet_temp_k, lambda temp_k: self.cp_j_kg_k(fluid, temp_k, pressure_pa).value)
        cp_mid = self.cp_j_kg_k(fluid, 0.5 * (inlet_temp_k + outlet_temp_k), pressure_pa)
        return PropertyResolution(value, cp_mid.source)

    def solve_outlet_temp_k(
        self,
        fluid: FluidSpec,
        inlet_temp_k: float,
        target_heat_release_j_kg: float,
        *,
        pressure_pa: float | None = None,
        minimum_temp_k: float,
        tolerance_j_kg: float = 1.0,
    ) -> tuple[float, float]:
        if target_heat_release_j_kg <= 0.0:
            return inlet_temp_k, 0.0

        lower = minimum_temp_k
        upper = inlet_temp_k
        achievable = self.heat_release_j_kg(fluid, inlet_temp_k, lower, pressure_pa).value
        if achievable <= target_heat_release_j_kg:
            return lower, achievable

        for _ in range(80):
            mid = 0.5 * (lower + upper)
            heat_mid = self.heat_release_j_kg(fluid, inlet_temp_k, mid, pressure_pa).value
            if abs(heat_mid - target_heat_release_j_kg) <= tolerance_j_kg:
                return mid, heat_mid
            if heat_mid > target_heat_release_j_kg:
                lower = mid
            else:
                upper = mid

        mid = 0.5 * (lower + upper)
        return mid, self.heat_release_j_kg(fluid, inlet_temp_k, mid, pressure_pa).value

    def _pure_component_cp_j_kg_k(
        self,
        *,
        component: dict[str, object],
        temp_k: float,
        pressure_pa: float,
        backend: PropertyBackend,
    ) -> tuple[float, str]:
        for candidate in self._backend_order(backend):
            if candidate is PropertyBackend.CANTERA:
                try:
                    return self._cantera_component_cp(component, temp_k, pressure_pa), "cantera"
                except Exception:
                    continue
            if candidate is PropertyBackend.COOLPROP:
                try:
                    return self._coolprop_component_cp(component, temp_k, pressure_pa), "coolprop"
                except Exception:
                    continue
            if candidate in {PropertyBackend.THERMO, PropertyBackend.CHEMICALS}:
                try:
                    return self._thermo_component_cp(component, temp_k, pressure_pa), "thermo"
                except Exception:
                    continue
            if candidate in {PropertyBackend.CORRELATION, PropertyBackend.MANUAL, PropertyBackend.AUTO}:
                return _evaluate_linear_cp(float(component["cp_a"]), float(component["cp_b"]), _temp_c(temp_k)), "correlation"
        raise ValueError(f"Could not resolve cp for component `{component['id']}`.")

    @staticmethod
    def _backend_order(backend: PropertyBackend) -> list[PropertyBackend]:
        if backend is PropertyBackend.AUTO:
            return [
                PropertyBackend.CANTERA,
                PropertyBackend.COOLPROP,
                PropertyBackend.THERMO,
                PropertyBackend.CORRELATION,
            ]
        return [backend]

    @staticmethod
    @lru_cache(maxsize=1)
    def _coolprop_props():
        from CoolProp.CoolProp import PropsSI  # type: ignore

        return PropsSI

    def _coolprop_component_cp(self, component: dict[str, object], temp_k: float, pressure_pa: float) -> float:
        if not backend_status()["coolprop"]:
            raise ValueError("CoolProp is not installed.")
        fluid_name = component.get("coolprop_name")
        if not fluid_name:
            raise ValueError("CoolProp mapping is missing.")
        props = self._coolprop_props()
        return float(props("C", "T", temp_k, "P", pressure_pa, str(fluid_name)))

    def _thermo_component_cp(self, component: dict[str, object], temp_k: float, pressure_pa: float) -> float:
        if not backend_status()["thermo"]:
            raise ValueError("thermo is not installed.")
        fluid_name = component.get("thermo_name")
        if not fluid_name:
            raise ValueError("thermo mapping is missing.")
        from thermo import Chemical  # type: ignore

        chemical = Chemical(str(fluid_name), T=temp_k, P=pressure_pa)
        return float(chemical.Cp)

    def _cantera_component_cp(self, component: dict[str, object], temp_k: float, pressure_pa: float) -> float:
        if not backend_status()["cantera"]:
            raise ValueError("Cantera is not installed.")
        import cantera as ct  # type: ignore

        gas = ct.Solution("gri30.yaml")
        gas.TPX = temp_k, pressure_pa, {str(component["id"]): 1.0}
        return float(gas.cp_mass)

