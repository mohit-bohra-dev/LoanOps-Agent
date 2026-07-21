from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LoanSummary(BaseModel):
    """Summary of a loan's current status and details."""

    loan_id: str
    borrower_first_name: str
    borrower_last_name: str
    state: str
    status: str
    product: str
    escrowed: bool
    current_balance_usd: float
    next_due_date: str | None
    delinquency_days: int
    last_payment_date: str | None
    flags: list[str]
    current_interest_rate: float | None = None
    monthly_pi_usd: float | None = None
    monthly_escrow_usd: float | None = None
    total_monthly_payment_usd: float | None = None
    maturity_date: str | None = None
    loan_active: bool | None = None
    investor_name: str | None = None


class PaymentScheduleItem(BaseModel):
    """A single payment period in a schedule."""

    due_date: str
    principal: float
    interest: float
    escrow: float
    total: float


class PaymentSchedule(BaseModel):
    """Upcoming payment schedule details."""

    loan_id: str
    schedule: list[PaymentScheduleItem]


class DisbursementItem(BaseModel):
    """An escrow disbursement record."""

    date: str
    type: str
    amount_usd: float


class EscrowBreakdown(BaseModel):
    """Escrow account breakdown and disbursement history."""

    loan_id: str
    as_of: str
    escrow_balance_usd: float
    monthly_escrow_usd: float
    monthly_escrow_change_usd: float
    change_effective: str
    drivers: list[str]
    last_disbursements: list[DisbursementItem]
    next_analysis_date: str


class EligibilityHint(BaseModel):
    """Non-binding hardship program eligibility hint."""

    loan_id: str
    program: str
    hint: str
    reasoning_factors: list[str]
    documentation_required: list[str]
    binding: bool = False
    next_step: str


class PolicyResultItem(BaseModel):
    """A single matched policy chunk from vector search."""

    chunk_id: str
    score: float
    snippet: str
    source_path: str
    version: str


class PolicyChunks(BaseModel):
    """Policy search query and matched results."""

    query: str
    state: str | None
    results: list[PolicyResultItem]


class CitationItem(BaseModel):
    """A citation backing a factual claim in agent turn output."""

    id: int
    source: str  # must start with 'policy:' or 'tool:'
    snippet: str


class ToolCallItem(BaseModel):
    """Record of a tool call made during agent execution."""

    name: str
    args: dict[str, Any]
    result_summary: str


class EscalationItem(BaseModel):
    """Escalation details when a conversation is escalated."""

    category: Literal["safety", "complaint_or_regulatory", "legal_status", "fraud", "identity"]
    reason: str


class AgentTurnOutput(BaseModel):
    """Structured output from a single agent turn."""

    answer: str
    citations: list[CitationItem]
    tool_calls: list[ToolCallItem] = Field(default_factory=list)
    requires_human_approval: Literal[True] = True
    confidence: float
    refusal: str | None = None
    escalation: EscalationItem | None = None
