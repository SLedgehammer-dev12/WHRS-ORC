from __future__ import annotations

import importlib.util
import json
from functools import lru_cache
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PACKAGE_ROOT / "data" / "fluids"


def _load_json_database(filename: str) -> list[dict[str, object]]:
    with (DATA_DIR / filename).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


EXHAUST_COMPONENTS = _load_json_database("exhaust_components.json")
THERMAL_OILS = _load_json_database("thermal_oils.json")

EXHAUST_COMPONENT_LIBRARY = {str(item["id"]): item for item in EXHAUST_COMPONENTS}
THERMAL_OIL_LIBRARY = {str(item.get("id", item["display_name"])): item for item in THERMAL_OILS}
THERMAL_OIL_BY_NAME = {str(item["display_name"]): item for item in THERMAL_OILS}


def module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


@lru_cache(maxsize=1)
def backend_status() -> dict[str, bool]:
    return {
        "cantera": module_available("cantera"),
        "coolprop": module_available("CoolProp"),
        "thermo": module_available("thermo"),
        "chemicals": module_available("chemicals"),
    }


def find_thermal_oil_record(fluid_id_or_name: str) -> dict[str, object] | None:
    return THERMAL_OIL_LIBRARY.get(fluid_id_or_name) or THERMAL_OIL_BY_NAME.get(fluid_id_or_name)
