from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    good = "good"
    needs_review = "needs_review"


@dataclass(frozen=True)
class ReviewSummary:
    verdict: Verdict
    text: str
    anomaly_count: int
    validation_error_count: int

    @classmethod
    def empty(cls) -> ReviewSummary:
        return cls(
            verdict=Verdict.good,
            text="",
            anomaly_count=0,
            validation_error_count=0,
        )
