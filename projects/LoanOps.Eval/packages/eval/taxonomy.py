"""Failure taxonomy for human error analysis (eval-improvement-platform)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

FAILURE_CATEGORIES: frozenset[str] = frozenset(
    {
        "wrong_api_selected",
        "missing_api",
        "incorrect_arguments",
        "missing_policy_context",
        "incorrect_answer",
        "unauthorized_access",
        "unnecessary_tool_calls",
        "hallucination",
        "sop_violation",
        "tool_error_unhandled",
        "other",
    }
)

ROOT_COMPONENTS: frozenset[str] = frozenset(
    {
        "capability_retrieval",
        "api_index",
        "eakg",
        "sop_retrieval",
        "graph_rag",
        "agent_planning",
        "agent_orchestration",
        "generation",
        "mcp_security",
        "mcp",
        "unknown",
    }
)

Severity = Literal["blocker", "major", "minor"]
ModelOutcome = Literal["good", "bad", "needs_review"]
FailLabels = frozenset({"fail", "bad", "incorrect"})
PassLabels = frozenset({"pass", "good", "approve", "approved", "needs_review"})

RECOMMENDED_ACTIONS: frozenset[str] = frozenset(
    {
        "add_mcp_tool",
        "remove_redundant_tool",
        "improve_tool_schema",
        "fix_retrieval_gap",
        "improve_prompt",
        "update_sop",
    }
)

REVIEW_FLAGS: frozenset[str] = frozenset(
    {
        "security",
        "compliance",
        "policy",
        "hallucination",
        "missing_info",
    }
)


class ReviewTaxonomy(BaseModel):
    """Structured fields attached to a human review label."""

    primary_category: str | None = None
    failure_categories: list[str] = Field(default_factory=list)
    severity: Severity | None = None
    root_component: str | None = None
    span_refs: list[str] = Field(default_factory=list)
    department: str | None = None
    adjudication_of: str | None = None
    highlight_note: str | None = None

    @field_validator("primary_category")
    @classmethod
    def _primary_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in FAILURE_CATEGORIES:
            raise ValueError(f"unknown primary_category: {v}")
        return v

    @field_validator("failure_categories")
    @classmethod
    def _cats_ok(cls, v: list[str]) -> list[str]:
        bad = [c for c in v if c not in FAILURE_CATEGORIES]
        if bad:
            raise ValueError(f"unknown failure_categories: {bad}")
        return v

    @field_validator("root_component")
    @classmethod
    def _root_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ROOT_COMPONENTS:
            raise ValueError(f"unknown root_component: {v}")
        return v


class FeedbackRequest(BaseModel):
    """API body for POST /eval/feedback."""

    trace_id: str
    label: str
    primary_category: str | None = None
    failure_categories: list[str] = Field(default_factory=list)
    severity: Severity | None = None
    root_component: str | None = None
    comment: str | None = None
    span_refs: list[str] = Field(default_factory=list)
    department: str | None = None
    queue: str = "loanops-error-analysis"
    rubric: str = "outcome"
    rubric_version: str = "1"
    reviewer: str = "anonymous"
    model_critique: str | None = None
    model_outcome: ModelOutcome | None = None
    suggested_answer: str | None = None
    recommended_action: str | None = None
    flags: list[str] = Field(default_factory=list)

    @field_validator("recommended_action")
    @classmethod
    def _action_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in RECOMMENDED_ACTIONS:
            raise ValueError(f"unknown recommended_action: {v}")
        return v

    @field_validator("flags")
    @classmethod
    def _flags_ok(cls, v: list[str]) -> list[str]:
        bad = [f for f in v if f not in REVIEW_FLAGS]
        if bad:
            raise ValueError(f"unknown flags: {bad}")
        return v

    @model_validator(mode="after")
    def _fail_requires_taxonomy(self) -> FeedbackRequest:
        lab = self.label.lower().strip()
        if lab in FailLabels:
            if not self.primary_category:
                raise ValueError("primary_category required when label is fail/bad")
            if self.severity is None:
                raise ValueError("severity required when label is fail/bad")
            tax = ReviewTaxonomy(
                primary_category=self.primary_category,
                failure_categories=self.failure_categories,
                severity=self.severity,
                root_component=self.root_component or "unknown",
                span_refs=self.span_refs,
                department=self.department,
            )
            _ = tax  # validate
        elif self.primary_category or self.failure_categories:
            _ = ReviewTaxonomy(
                primary_category=self.primary_category,
                failure_categories=self.failure_categories,
                severity=self.severity,
                root_component=self.root_component,
                span_refs=self.span_refs,
                department=self.department,
            )
        return self

    def taxonomy(self) -> ReviewTaxonomy | None:
        if not self.primary_category and not self.failure_categories and self.severity is None:
            return None
        return ReviewTaxonomy(
            primary_category=self.primary_category,
            failure_categories=list(self.failure_categories),
            severity=self.severity,
            root_component=self.root_component,
            span_refs=list(self.span_refs),
            department=self.department,
        )


def is_promotable_label(label: str) -> bool:
    """Fail cases (regression) or explicit approve labels may enter candidates."""
    lab = label.lower().strip()
    return lab in FailLabels or lab in PassLabels
