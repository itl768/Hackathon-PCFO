from __future__ import annotations

from typing import Any

from api.invoicing.domain import Finding


def findings_to_output(findings: list[Finding]) -> list[dict[str, Any]]:
    return [
        {
            "field_path": f.field_path,
            "message": f.message,
            "severity": f.severity.value,
        }
        for f in findings
    ]
