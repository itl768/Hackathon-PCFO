from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from api.invoicing.application.ports import ReviewSummaryService
from api.invoicing.domain import ExtractionResult, Finding, Verdict

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You write short review summaries for accounts payable staff.

Given structured invoice extraction data and any anomaly or validation findings, write 2-4 plain-English sentences that:
- State whether the invoice looks ready to pay or needs human review
- Mention the most important missing fields, anomalies, or validation issues (if any)
- Do not invent amounts, dates, vendors, or line items not present in the payload
- Do not use bullet lists; use flowing prose only
"""


class OpenAIReviewSummaryService(ReviewSummaryService):
    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
        max_retries: int,
        request_timeout_seconds: int,
    ) -> None:
        self._client = client
        self._model = model
        self._max_retries = max_retries
        self._request_timeout_seconds = request_timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    async def summarize(
        self,
        *,
        extraction: ExtractionResult,
        anomalies: list[Finding],
        validation_errors: list[Finding],
        verdict: Verdict,
    ) -> str:
        user_payload = _build_payload(
            extraction=extraction,
            anomalies=anomalies,
            validation_errors=validation_errors,
            verdict=verdict,
        )
        started = time.monotonic()
        try:
            text = await self._call_openai(user_payload)
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.info("Responder summary completed in %dms using %s", latency_ms, self._model)
            return text.strip()
        except Exception:
            logger.exception("Responder summary failed; using fallback")
            return _fallback_summary(
                verdict=verdict,
                anomaly_count=len(anomalies),
                validation_error_count=len(validation_errors),
            )

    async def _call_openai(self, user_payload: dict[str, Any]) -> str:
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(
                (RateLimitError, APITimeoutError, APIConnectionError)
            ),
            reraise=True,
        )

        async for attempt in retrying:
            with attempt:
                completion = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(user_payload, indent=2),
                        },
                    ],
                    timeout=self._request_timeout_seconds,
                )
                message = completion.choices[0].message
                content = message.content
                if not content:
                    raise ValueError("Model returned empty summary")
                return content

        raise RuntimeError("Responder exhausted retries without a response")


def _build_payload(
    *,
    extraction: ExtractionResult,
    anomalies: list[Finding],
    validation_errors: list[Finding],
    verdict: Verdict,
) -> dict[str, Any]:
    return {
        "verdict": verdict.value,
        "extraction": _extraction_to_dict(extraction),
        "anomalies": [_finding_to_dict(f) for f in anomalies],
        "validation_errors": [_finding_to_dict(f) for f in validation_errors],
    }


def _extraction_to_dict(extraction: ExtractionResult) -> dict[str, Any]:
    data = extraction.model_dump(mode="json")
    return data


def _finding_to_dict(finding: Finding) -> dict[str, str]:
    return {
        "field_path": finding.field_path,
        "message": finding.message,
        "severity": finding.severity.value,
        "source_agent": finding.source_agent,
    }


def _fallback_summary(
    *,
    verdict: Verdict,
    anomaly_count: int,
    validation_error_count: int,
) -> str:
    if verdict is Verdict.good:
        return (
            "The invoice passed automated review with no anomalies or validation issues. "
            "It appears ready for payment."
        )
    parts: list[str] = []
    if anomaly_count:
        parts.append(f"{anomaly_count} anomal{'y' if anomaly_count == 1 else 'ies'}")
    if validation_error_count:
        parts.append(
            f"{validation_error_count} validation issue"
            f"{'' if validation_error_count == 1 else 's'}"
        )
    joined = " and ".join(parts) if parts else "issues"
    return (
        f"This invoice needs human review: {joined} were detected during automated checks. "
        "Please verify the highlighted fields before approving payment."
    )
