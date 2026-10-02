from __future__ import annotations

import uuid

from packages.common.providers.audit_sink import AuditEvent, AuditSinkProvider
from packages.common.providers.content_safety import ContentSafetyProvider
from packages.common.providers.pii import PiiProvider

from .models import EvaluationResult, SanitizeResult
from .models import PiiSpan as MiddlewarePiiSpan
from .tokenizer import PiiTokenizer


async def sanitize_inbound(
    text: str,
    pii_provider: PiiProvider,
    audit_provider: AuditSinkProvider,
) -> SanitizeResult:
    """
    PII tokenise inbound prompt. Write PII audit event.

    Instead of destructively replacing PII with ``<PERSON>`` etc., this
    produces reversible numbered tokens (``[PERSON_1]``) and returns the
    token map so the tools layer can detokenize within the trust boundary.
    """
    result = await pii_provider.anonymise(text)

    # Build middleware-level PII spans from the provider result
    middleware_spans = [
        MiddlewarePiiSpan(
            entity_type=span.entity_type,
            start=span.start,
            end=span.end,
            original_text=text[span.start : span.end],
        )
        for span in result.entities
    ]

    # Tokenize: replace PII with numbered tokens (e.g. [PERSON_1])
    tokenized_text, token_map = PiiTokenizer.tokenize(text, middleware_spans)

    # Write PII audit event (tokenized text, NOT original PII)
    await audit_provider.emit(
        AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type="pii.redacted",
            payload={
                "original_text": tokenized_text,  # tokens only — no real PII in audit
                "anonymized_text": tokenized_text,
                "spans": [
                    {
                        "entity_type": span.entity_type,
                        "start": span.start,
                        "end": span.end,
                        "token": f"[{span.entity_type}_{i + 1}]",
                    }
                    for i, span in enumerate(sorted(result.entities, key=lambda s: s.start))
                ],
            },
        )
    )

    return SanitizeResult(
        anonymized_text=tokenized_text,
        spans=middleware_spans,
        token_map=token_map,
    )


async def evaluate_outbound(
    text: str,
    safety_provider: ContentSafetyProvider,
    audit_provider: AuditSinkProvider,
) -> EvaluationResult:
    """
    Content safety check outbound answer. Write safety audit event.
    """
    result = await safety_provider.check(text)

    # Write safety audit event
    await audit_provider.emit(
        AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type="safety.evaluated",
            payload={
                "original_text": text,
                "verdict": result.verdict.value,
                "reason": result.reason,
                "score": result.score,
            },
        )
    )

    return EvaluationResult(
        is_safe=result.verdict.name == "SAFE",
        original_text=text,
        blocked_text=None if result.verdict.name == "SAFE" else text,
        verdict=result.verdict.value,
        reason=result.reason,
    )


class SafetyPipeline:
    """
    Convenience wrapper for the safety middleware.
    Obtains providers from factories for production use.
    """

    def __init__(self) -> None:
        from packages.common.providers.factory import (
            get_audit_sink_provider,
            get_content_safety_provider,
            get_pii_provider,
        )

        self._pii = get_pii_provider()
        self._safety = get_content_safety_provider()
        self._audit = get_audit_sink_provider()

    async def sanitize_inbound(self, text: str) -> SanitizeResult:
        return await sanitize_inbound(text, self._pii, self._audit)

    async def evaluate_outbound(self, text: str) -> EvaluationResult:
        return await evaluate_outbound(text, self._safety, self._audit)
