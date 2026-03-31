from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from whrs_orc import __version__
from whrs_orc.reporting.screening_report import build_screening_report_payload
from whrs_orc.solvers.screening_case import ScreeningCaseInputs, ScreeningCaseResult


def build_screening_run_log_record(
    case: ScreeningCaseInputs,
    result: ScreeningCaseResult,
    *,
    event_type: str = "screening_case_solved",
    logged_at_utc: datetime | None = None,
) -> dict[str, object]:
    timestamp = logged_at_utc or datetime.now(UTC)
    payload = build_screening_report_payload(case, result, generated_at_utc=timestamp)
    statuses = {
        "boiler": str(result.boiler_result.status),
        "oil_loop": str(result.loop_result.status) if result.loop_result is not None else None,
        "orc_heat": str(result.orc_heat_result.status) if result.orc_heat_result is not None else None,
        "orc_power": str(result.orc_power_result.status) if result.orc_power_result is not None else None,
    }
    blocked = any(
        envelope is not None and envelope.blocked_state.blocked
        for envelope in [result.boiler_result, result.loop_result, result.orc_heat_result, result.orc_power_result]
    )
    warning_count = sum(
        len(envelope.warnings)
        for envelope in [result.boiler_result, result.loop_result, result.orc_heat_result, result.orc_power_result]
        if envelope is not None
    )
    return {
        "schema_version": "1.0",
        "event_type": event_type,
        "logged_at_utc": timestamp.isoformat(),
        "app_version": __version__,
        "case_name": case.case_name,
        "blocked": blocked,
        "warning_count": warning_count,
        "statuses": statuses,
        "kpis": payload["kpis"],
        "operator_guidance": payload["operator_guidance"],
    }


def append_jsonl_record(path: str | Path, record: dict[str, object]) -> Path:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return target_path


def log_screening_case_run(
    path: str | Path,
    case: ScreeningCaseInputs,
    result: ScreeningCaseResult,
    *,
    event_type: str = "screening_case_solved",
    logged_at_utc: datetime | None = None,
) -> Path:
    record = build_screening_run_log_record(case, result, event_type=event_type, logged_at_utc=logged_at_utc)
    return append_jsonl_record(path, record)
