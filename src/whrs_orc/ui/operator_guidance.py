from __future__ import annotations

from dataclasses import dataclass

from whrs_orc.domain.result_schema import ResultEnvelope
from whrs_orc.solvers.screening_case import ScreeningCaseResult


@dataclass(frozen=True, slots=True)
class GuidanceNote:
    severity: str
    title: str
    detail: str


def build_operator_guidance(result: ScreeningCaseResult | None) -> list[GuidanceNote]:
    if result is None:
        return [
            GuidanceNote(
                severity="info",
                title="Solve bekleniyor",
                detail="Bir vaka calistirdiginizda bu alan fiziksel gecerlilik ve operator aksiyonlarini ozetleyecek.",
            )
        ]

    notes: list[GuidanceNote] = []
    module_results = [
        ("Boiler", result.boiler_result),
        ("Oil Loop", result.loop_result),
        ("ORC Heat", result.orc_heat_result),
        ("ORC Power", result.orc_power_result),
    ]
    for module_name, envelope in module_results:
        if envelope is None:
            continue
        notes.extend(_guidance_for_envelope(module_name, envelope))

    if notes:
        return notes

    gross_power = None
    if result.orc_power_result is not None:
        metric = result.orc_power_result.values.get("gross_electric_power_w")
        gross_power = metric.value_si if metric is not None else None
    detail = (
        f"Screening zinciri fiziksel olarak kapandi. Tahmini brut elektrik gucu {gross_power / 1000.0:,.1f} kW."
        if gross_power is not None
        else "Screening zinciri fiziksel olarak kapandi. KPI ve diagnostics panelleri ile sonuclari gozden gecirebilirsiniz."
    )
    return [GuidanceNote(severity="info", title="Vaka screening seviyesinde tutarli", detail=detail)]


def render_operator_guidance(notes: list[GuidanceNote]) -> str:
    lines: list[str] = []
    for note in notes:
        lines.append(f"[{note.severity.upper()}] {note.title}")
        lines.append(note.detail)
        lines.append("")
    return "\n".join(lines).strip()


def _guidance_for_envelope(module_name: str, envelope: ResultEnvelope) -> list[GuidanceNote]:
    notes: list[GuidanceNote] = []

    if envelope.blocked_state.blocked:
        notes.append(_blocked_note(module_name, envelope))
        return notes

    for warning in envelope.warnings:
        if warning.code == "VAL-BOILER-002":
            notes.append(
                GuidanceNote(
                    severity="warning",
                    title=f"{module_name}: enerji kapanisi tolerans disinda",
                    detail=(
                        "Egzoz tarafi ile yag tarafi isi dengesi secilen toleransin disinda. "
                        "Debi, sicaklik ve ozellik verilerinin ayni calisma anina ait oldugunu dogrulayin; "
                        "gerekirse egzoz cikis sicakligi, yag cikis sicakligi ve yag debisini tekrar gozden gecirin."
                    ),
                )
            )
        else:
            notes.append(
                GuidanceNote(
                    severity="warning",
                    title=f"{module_name}: uyari",
                    detail=warning.message,
                )
            )
    return notes


def _blocked_note(module_name: str, envelope: ResultEnvelope) -> GuidanceNote:
    blocked = envelope.blocked_state
    code = blocked.code or "-"

    if code == "VAL-HX-003":
        exchanger_name = "kazan icinde" if module_name == "Boiler" else "isi degistirici icinde"
        return GuidanceNote(
            severity="critical",
            title=f"{module_name}: fiziksel olmayan sicaklik yaklasimi",
            detail=(
                f"{exchanger_name.capitalize()} sicaklik caprazi veya izin verilen minimum yaklasimin altina dusen bir nokta olustu. "
                "Egzoz cikis sicakligini yukseltin, yag giris sicakligini dusurun, hedef yag cikis sicakligini azaltin "
                "veya debi/olcum setinin ayni calisma kosuluna ait oldugunu kontrol edin."
            ),
        )
    if code == "VAL-STACK-001":
        return GuidanceNote(
            severity="critical",
            title=f"{module_name}: stack sicakligi siniri asildi",
            detail=(
                "Secilen nokta stack minimum sicakliginin altina iniyor. "
                "Minimum stack hedefini artirin veya kazan duty talebini dusurun."
            ),
        )

    detail = blocked.reason or f"{module_name} sonucu bloklandi."
    if blocked.suggested_action:
        detail = f"{detail} Oneri: {blocked.suggested_action}"
    return GuidanceNote(
        severity="critical",
        title=f"{module_name}: cozum bloklandi",
        detail=detail,
    )
