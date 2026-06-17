"""Intent router — a pure function that classifies a rep's prompt into an intent.

The router uses keyword / pattern matching to identify escalation triggers
and refusal scenarios BEFORE the LLM is called. This is a safety gate that
runs synchronously and does not import any concrete provider class.
"""

from __future__ import annotations

from enum import StrEnum


class IntentType(StrEnum):
    """The three possible intents for an agent turn."""

    ANSWER = "answer"
    REFUSE = "refuse"
    ESCALATE = "escalate"


# ── Escalation trigger keywords (from Section B of the system prompt) ──────
_ESCALATION_PATTERNS: list[tuple[frozenset[str], str]] = [
    # Safety: self-harm / suicide / threats / violence
    (
        frozenset({"suicide", "kill myself", "self-harm", "self harm", "hurt myself"}),
        "safety",
    ),
    (
        frozenset({"threat", "domestic violence", "violent"}),
        "safety",
    ),
    # Complaint / regulatory
    (
        frozenset({"cfpb", "attorney", "lawsuit", "regulator", "bbb", "complaint"}),
        "complaint_or_regulatory",
    ),
    (
        frozenset({"written complaint", "qwr", "notice of error", "noe"}),
        "complaint_or_regulatory",
    ),
    # Legal status
    (
        frozenset({"bankruptcy", "foreclosure stop", "active litigation", "litigation"}),
        "legal_status",
    ),
    # Fraud / identity theft
    (
        frozenset({"identity theft", "fraud", "unauthorized access", "unauthorized"}),
        "fraud",
    ),
    # Identity verification
    (
        frozenset({"identity verification", "verify identity", "who is this"}),
        "identity",
    ),
]

# ── Refusal patterns (out-of-scope topics) ─────────────────────────────────
_REFUSAL_PATTERNS: list[tuple[frozenset[str], str]] = [
    (
        frozenset({"rate quote", "what rate", "apr", "interest rate quote", "refinance rate"}),
        "This request is outside v1 scope (rate quoting). Route to the Originations queue.",
    ),
    (
        frozenset({"advice", "should i", "should the borrower", "should borrower", "recommend"}),
        "This request is outside v1 scope (financial advice). Route to the appropriate queue.",
    ),
    (
        frozenset({"mutating", "make payment", "post payment", "start forbearance"}),
        "This request requires a mutating action,"
        " which is outside v1 scope. Route to the appropriate servicing team.",
    ),
    (
        frozenset({"payoff quote", "payoff amount", "payoff letter"}),
        "Payoff quotes require a formal payoff department request and are outside v1 scope.",
    ),
]


def classify_intent(prompt: str) -> tuple[IntentType, str, str | None]:
    """Classify a rep prompt into an intent.

    Returns a tuple of ``(intent_type, reason_or_category, detail)``.

    For ``ANSWER`` intents, ``detail`` is ``None`` and ``reason_or_category``
    is ``"answer"``.

    For ``REFUSE`` intents, ``reason_or_category`` is a human-readable refusal
    message and ``detail`` is ``None``.

    For ``ESCALATE`` intents, ``reason_or_category`` is the escalation category
    (one of ``"safety"``, ``"complaint_or_regulatory"``, ``"legal_status"``,
    ``"fraud"``, ``"identity"``) and ``detail`` is a short justification.
    """
    prompt_lower = prompt.lower()

    # Check escalation patterns first (safety-critical)
    for keywords, category in _ESCALATION_PATTERNS:
        if any(kw in prompt_lower for kw in keywords):
            return (
                IntentType.ESCALATE,
                category,
                f"Trigger detected: matched '{category}' escalation pattern",
            )

    # Check refusal patterns
    for keywords, reason in _REFUSAL_PATTERNS:
        if any(kw in prompt_lower for kw in keywords):
            return (IntentType.REFUSE, reason, None)

    # Default: answer
    return (IntentType.ANSWER, "answer", None)
