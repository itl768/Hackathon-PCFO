from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class FindingKind(str, Enum):
    anomaly = "anomaly"
    validation_error = "validation_error"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


@dataclass(frozen=True)
class Finding:
    kind: FindingKind
    severity: Severity
    field_path: str
    message: str
    source_agent: str
    detected_at: datetime

    @classmethod
    def anomaly(
        cls,
        *,
        field_path: str,
        message: str,
        source_agent: str,
        severity: Severity = Severity.medium,
    ) -> Finding:
        return cls(
            kind=FindingKind.anomaly,
            severity=severity,
            field_path=field_path,
            message=message,
            source_agent=source_agent,
            detected_at=datetime.now(UTC),
        )

    @classmethod
    def validation_error(
        cls,
        *,
        field_path: str,
        message: str,
        source_agent: str,
        severity: Severity = Severity.medium,
    ) -> Finding:
        return cls(
            kind=FindingKind.validation_error,
            severity=severity,
            field_path=field_path,
            message=message,
            source_agent=source_agent,
            detected_at=datetime.now(UTC),
        )
