from __future__ import annotations

from dataclasses import dataclass

from whrs_orc.equipment.contracts import (
    BoilerDesignDriver,
    BoilerMode,
    OrcScreeningHeatMode,
    OrcScreeningPowerMode,
    ThermalOilLoopMode,
)


@dataclass(frozen=True, slots=True)
class FieldPresentation:
    label: str
    unit_hint: str
    helper_text: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class UiBehaviorState:
    study_title: str
    study_helper: str
    design_target: FieldPresentation
    exhaust_outlet_enabled: bool
    oil_outlet_enabled: bool
    loop_heat_loss_enabled: bool
    loop_target_delivery_enabled: bool
    orc_target_wf_outlet_enabled: bool
    orc_known_heat_input_enabled: bool
    orc_efficiency_enabled: bool
    gross_power_target_enabled: bool
    oil_manual_properties_enabled: bool
    wf_manual_properties_enabled: bool


_DRIVER_PRESENTATIONS: dict[BoilerDesignDriver, FieldPresentation] = {
    BoilerDesignDriver.MINIMUM_STACK_TEMPERATURE: FieldPresentation(
        label="Hedef minimum stack sicakligi",
        unit_hint="degC",
        helper_text="Program egzoz cikisini secilen stack taban sicakligina kadar sogutarak kazan isi transferini cozer.",
    ),
    BoilerDesignDriver.TARGET_BOILER_EFFICIENCY: FieldPresentation(
        label="Hedef kazan verimi",
        unit_hint="0-1",
        helper_text="Kullanici, mevcut egzoz kullanilabilir isisinin ne kadarinin yaga aktarilacagini oran olarak belirler.",
    ),
    BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE: FieldPresentation(
        label="Hedef yag cikis sicakligi",
        unit_hint="degC",
        helper_text="Program secilen yag debisi ve giris sicakligi ile hedef yag cikis sicakligina gore duty hesaplar.",
    ),
    BoilerDesignDriver.TARGET_TRANSFERRED_POWER: FieldPresentation(
        label="Hedef transfer edilen guc",
        unit_hint="W",
        helper_text="Ilk kodlama turunda planli ama henuz aktif degil.",
    ),
    BoilerDesignDriver.TARGET_EFFECTIVENESS: FieldPresentation(
        label="Hedef esanjur effectiveness",
        unit_hint="0-1",
        helper_text="Ilk kodlama turunda planli ama henuz aktif degil.",
    ),
    BoilerDesignDriver.TARGET_UA: FieldPresentation(
        label="Hedef UA",
        unit_hint="W/K",
        helper_text="Ilk kodlama turunda planli ama henuz aktif degil.",
    ),
    BoilerDesignDriver.MINIMUM_PINCH_APPROACH: FieldPresentation(
        label="Minimum pinch yaklasimi",
        unit_hint="K",
        helper_text="Ilk kodlama turunda planli ama henuz aktif degil.",
    ),
}

_DISABLED_DESIGN_TARGET = FieldPresentation(
    label="Tasarim hedefi",
    unit_hint="-",
    helper_text="Mevcut tesis analizi modunda tasarim hedefi kullanilmaz.",
    enabled=False,
)


def build_ui_behavior_state(
    boiler_mode: BoilerMode,
    boiler_driver: BoilerDesignDriver,
    loop_mode: ThermalOilLoopMode,
    orc_heat_mode: OrcScreeningHeatMode,
    orc_power_mode: OrcScreeningPowerMode,
    oil_name: str,
    wf_name: str,
) -> UiBehaviorState:
    is_design = boiler_mode is BoilerMode.DESIGN
    study_title = "Tasarim calismasi" if is_design else "Mevcut tesis analizi"
    study_helper = (
        "Kullanici tek bir tasarim surucusu secer; program geri kalan performansi fiziksel kisitlarla cozer."
        if is_design
        else "Sahadan girilen giris ve cikis degerlerine gore kazan, ORC isi alimi ve brut guc degerlendirilir."
    )
    design_target = _DRIVER_PRESENTATIONS[boiler_driver] if is_design else _DISABLED_DESIGN_TARGET
    manual_wf_names = {"manual working fluid", "manual wf"}

    return UiBehaviorState(
        study_title=study_title,
        study_helper=study_helper,
        design_target=design_target,
        exhaust_outlet_enabled=not is_design,
        oil_outlet_enabled=not is_design,
        loop_heat_loss_enabled=loop_mode is ThermalOilLoopMode.RATED_HEAT_LOSS,
        loop_target_delivery_enabled=loop_mode is ThermalOilLoopMode.TARGET_DELIVERY_TEMPERATURE,
        orc_target_wf_outlet_enabled=orc_heat_mode is OrcScreeningHeatMode.SINGLE_PHASE_TEMPERATURE_GAIN,
        orc_known_heat_input_enabled=orc_heat_mode is OrcScreeningHeatMode.KNOWN_ORC_HEAT_INPUT,
        orc_efficiency_enabled=orc_power_mode is OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY,
        gross_power_target_enabled=orc_power_mode is OrcScreeningPowerMode.GROSS_EFFICIENCY_FROM_POWER,
        oil_manual_properties_enabled=oil_name == "Manual Oil",
        wf_manual_properties_enabled=wf_name.lower() in manual_wf_names,
    )
