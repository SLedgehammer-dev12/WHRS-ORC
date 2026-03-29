from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from whrs_orc.domain.models import ProcessStream


class ResultStatus(StrEnum):
    SUCCESS = "success"
    WARNING = "warning"
    BLOCKED = "blocked"
    ERROR = "error"


class WarningSeverity(StrEnum):
    INFO = "info"
    SOFT_WARNING = "soft_warning"
    HARD_WARNING = "hard_warning"


@dataclass(slots=True)
class MetricValue:
    key: str
    display_name: str
    value_si: float
    unit_si: str
    display_unit: str | None = None
    display_value: float | None = None
    basis: str | None = None
    source: str | None = None
    lower_bound_si: float | None = None
    upper_bound_si: float | None = None
    notes: str | None = None


@dataclass(slots=True)
class WarningRecord:
    code: str
    message: str
    severity: WarningSeverity = WarningSeverity.SOFT_WARNING
    source: str | None = None
    affected_object: str | None = None
    recommended_action: str | None = None


@dataclass(slots=True)
class AssumptionRecord:
    code: str
    message: str
    source: str | None = None
    impact_level: str | None = None
    applied_value: float | str | None = None


@dataclass(slots=True)
class CalcTraceEntry:
    step: str
    message: str
    equation_ref: str | None = None
    value_snapshot: dict[str, float | int | str] = field(default_factory=dict)
    backend_used: str | None = None
    duration_ms: float | None = None


@dataclass(slots=True)
class BlockedState:
    blocked: bool = False
    code: str | None = None
    reason: str | None = None
    source: str | None = None
    suggested_action: str | None = None


@dataclass(slots=True)
class ResultEnvelope:
    result_id: str
    model_name: str
    model_version: str
    status: ResultStatus
    values: dict[str, MetricValue] = field(default_factory=dict)
    warnings: list[WarningRecord] = field(default_factory=list)
    assumptions: list[AssumptionRecord] = field(default_factory=list)
    calc_trace: list[CalcTraceEntry] = field(default_factory=list)
    blocked_state: BlockedState = field(default_factory=BlockedState)
    metadata: dict[str, Any] = field(default_factory=dict)
    solved_streams: dict[str, ProcessStream] = field(default_factory=dict)
    tables: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    input_echo: dict[str, Any] = field(default_factory=dict)

    def add_metric(self, metric: MetricValue) -> None:
        self.values[metric.key] = metric

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def blocked_result(
        cls,
        *,
        result_id: str,
        model_name: str,
        model_version: str,
        code: str,
        reason: str,
        source: str,
        suggested_action: str | None = None,
        warnings: list[WarningRecord] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ResultEnvelope":
        return cls(
            result_id=result_id,
            model_name=model_name,
            model_version=model_version,
            status=ResultStatus.BLOCKED,
            warnings=warnings or [],
            blocked_state=BlockedState(
                blocked=True,
                code=code,
                reason=reason,
                source=source,
                suggested_action=suggested_action,
            ),
            metadata=metadata or {},
        )

