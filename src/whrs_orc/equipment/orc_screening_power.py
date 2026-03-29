from __future__ import annotations

from uuid import uuid4

from whrs_orc.domain.result_schema import AssumptionRecord, CalcTraceEntry, MetricValue, ResultEnvelope, ResultStatus
from whrs_orc.equipment.contracts import OrcScreeningPowerMode, OrcScreeningPowerRequest


MODEL_NAME = "orc_screening_power"
MODEL_VERSION = "0.1.0"


def solve_orc_screening_power(request: OrcScreeningPowerRequest) -> ResultEnvelope:
    if request.q_orc_absorbed_w <= 0.0:
        return _blocked("VAL-ORC-004", "ORC absorbed heat must be positive for screening power calculation.", request)

    if request.mode is OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY:
        if request.eta_orc_gross_target is None:
            return _blocked("VAL-ORC-008", "Gross-power-from-efficiency mode requires `eta_orc_gross_target`.", request)
        eta_orc_gross = request.eta_orc_gross_target
        if eta_orc_gross < 0.0 or eta_orc_gross > 1.0:
            return _blocked("VAL-ORC-003", "ORC gross efficiency must be between 0 and 1.", request)
        gross_electric_power_w = eta_orc_gross * request.q_orc_absorbed_w
    elif request.mode is OrcScreeningPowerMode.GROSS_EFFICIENCY_FROM_POWER:
        if request.gross_electric_power_target_w is None:
            return _blocked("VAL-ORC-009", "Gross-efficiency-from-power mode requires `gross_electric_power_target_w`.", request)
        gross_electric_power_w = request.gross_electric_power_target_w
        if gross_electric_power_w < 0.0 or gross_electric_power_w > request.q_orc_absorbed_w:
            return _blocked("VAL-ORC-004", "Gross electric power cannot exceed absorbed ORC heat in screening mode.", request)
        eta_orc_gross = gross_electric_power_w / request.q_orc_absorbed_w
    else:
        return _blocked("VAL-MODE-001", f"Unsupported ORC screening power mode `{request.mode}`.", request)

    result = ResultEnvelope(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        status=ResultStatus.SUCCESS,
        metadata={"calculation_mode": request.mode},
    )
    result.add_metric(MetricValue("gross_electric_power_w", "Gross Electric Power", gross_electric_power_w, "W"))
    result.add_metric(MetricValue("eta_orc_gross", "ORC Gross Efficiency", eta_orc_gross, "1"))
    if request.q_exhaust_available_w is not None and request.q_exhaust_available_w > 0.0:
        result.add_metric(
            MetricValue(
                "eta_system_gross",
                "Gross System Efficiency",
                gross_electric_power_w / request.q_exhaust_available_w,
                "1",
            )
        )
    result.assumptions.append(
        AssumptionRecord(
            code="ASM-ORC-002",
            message="Gross electric power is estimated from absorbed ORC heat using a screening efficiency basis.",
            source="orc_screening_power",
        )
    )
    result.calc_trace.append(
        CalcTraceEntry(
            step="orc_screening_power",
            message="Calculated ORC screening gross power and gross efficiency.",
            value_snapshot={
                "q_orc_absorbed_w": request.q_orc_absorbed_w,
                "gross_electric_power_w": gross_electric_power_w,
                "eta_orc_gross": eta_orc_gross,
            },
        )
    )
    return result


def _blocked(code: str, reason: str, request: OrcScreeningPowerRequest, *, source: str = "orc_screening_power") -> ResultEnvelope:
    return ResultEnvelope.blocked_result(
        result_id=str(uuid4()),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        code=code,
        reason=reason,
        source=source,
        metadata={"calculation_mode": request.mode},
    )
