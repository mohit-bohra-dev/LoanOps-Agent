"""In-process SSE fixture — mock loan endpoints without a second HTTP server."""

from __future__ import annotations

from typing import Any


FIXTURE_OPENAPI: dict[str, Any] = {
    "openapi": "3.0.0",
    "info": {"title": "SSE Fixture", "version": "1.0.0"},
    "servers": [{"url": "https://fixture.local"}],
    "paths": {
        "/api/Loans/{loan_id}": {
            "get": {
                "operationId": "getLoan",
                "summary": "Get loan by id",
                "tags": ["loans"],
                "parameters": [
                    {
                        "name": "loan_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/api/Loans/{loan_id}/PaymentSchedules": {
            "get": {
                "operationId": "getPaymentSchedules",
                "summary": "Get payment schedule for loan",
                "tags": ["payments"],
                "parameters": [
                    {
                        "name": "loan_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
    },
}


def fixture_loan(loan_id: str) -> dict[str, Any]:
    return {
        "loanId": loan_id,
        "status": "Current",
        "investor": "FNMA",
        "unpaidPrincipalBalance": 250000.0,
        "nextDueDate": "2026-10-01",
        "citation": "tool:fixture.getLoan",
    }


def fixture_payments(loan_id: str) -> dict[str, Any]:
    return {
        "loanId": loan_id,
        "schedules": [
            {"dueDate": "2026-10-01", "amount": 1850.25},
            {"dueDate": "2026-11-01", "amount": 1850.25},
        ],
        "citation": "tool:fixture.getPaymentSchedules",
    }
