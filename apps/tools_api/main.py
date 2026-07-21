from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from provider_contracts.vector_store import SearchResult
from pydantic import BaseModel

from packages.common import schemas
from packages.common.providers.factory import (
    get_embedding_provider,
    get_loan_data_provider,
    get_vector_store_provider,
)
from packages.common.settings import Settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Servicing Tools API",
    description="Mock servicing API endpoints for the Servicing Agent",
    version="1.0.0",
    docs_url="/",
    redoc_url=None,
)

security = HTTPBearer()
settings = Settings()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:  # noqa: B008
    """Verify that the Bearer token matches the configured TOOLS_API_TOKEN."""
    token = credentials.credentials
    expected_token = settings.tools_api_token
    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
        )
    return token


# ── Request Models ─────────────────────────────────────────────────────────


class LookupLoanRequest(BaseModel):
    loan_id: str


class GetPaymentScheduleRequest(BaseModel):
    loan_id: str
    months: int = 3


class GetEscrowBreakdownRequest(BaseModel):
    loan_id: str


class CheckHardshipEligibilityRequest(BaseModel):
    loan_id: str
    program: str


class SearchPolicyRequest(BaseModel):
    query: str
    state: str | None = None
    k: int = 5


class SearchBorrowerRequest(BaseModel):
    name: str


# ── Utility Helpers ────────────────────────────────────────────────────────


def get_loan_or_404(loan_id: str) -> dict[str, Any]:
    """Retrieve loan from the database or raise 404."""
    raise NotImplementedError("Use async_get_loan_or_404 instead")

async def async_get_loan_or_404(loan_id: str) -> dict[str, Any]:
    """Retrieve loan from the data provider or raise 404."""
    # Strip whitespace to handle LLM formatting quirks
    clean_loan_id = loan_id.strip()

    provider = get_loan_data_provider()
    loan = await provider.get_loan(clean_loan_id)
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan ID {clean_loan_id} not found",
        )
    return loan


def to_loan_summary(loan: dict[str, Any]) -> schemas.LoanSummary:
    """Convert a raw loan record into the LoanSummary response model."""
    return schemas.LoanSummary(
        loan_id=loan["loan_id"],
        borrower_first_name=loan["borrower_first_name"],
        borrower_last_name=loan["borrower_last_name"],
        state=loan["state"],
        status=loan["status"],
        product=loan["product"],
        escrowed=loan["escrowed"],
        current_balance_usd=loan["current_balance_usd"],
        next_due_date=loan["next_due_date"],
        delinquency_days=loan["delinquency_days"],
        last_payment_date=loan.get("last_payment_date"),
        flags=loan["flags"],
        current_interest_rate=loan.get("current_interest_rate"),
        monthly_pi_usd=loan.get("monthly_pi_usd"),
        monthly_escrow_usd=loan.get("monthly_escrow_usd"),
        total_monthly_payment_usd=loan.get("total_monthly_payment_usd"),
        maturity_date=loan.get("maturity_date"),
        loan_active=loan.get("loan_active"),
        investor_name=loan.get("investor_name"),
    )


async def search_loans_by_borrower_name(name: str) -> list[schemas.LoanSummary]:
    """Search loan records by borrower name."""
    provider = get_loan_data_provider()
    matches = await provider.search_by_name(name)
    return [to_loan_summary(loan) for loan in matches]


def to_payment_schedule(data: dict[str, Any]) -> schemas.PaymentSchedule:
    """Convert provider payment schedule dict into response model."""
    return schemas.PaymentSchedule(
        loan_id=data["loan_id"],
        schedule=[schemas.PaymentScheduleItem(**item) for item in data["schedule"]],
    )


def to_escrow_breakdown(data: dict[str, Any]) -> schemas.EscrowBreakdown:
    """Convert provider escrow breakdown dict into response model."""
    return schemas.EscrowBreakdown(
        loan_id=data["loan_id"],
        as_of=data["as_of"],
        escrow_balance_usd=data["escrow_balance_usd"],
        monthly_escrow_usd=data["monthly_escrow_usd"],
        monthly_escrow_change_usd=data["monthly_escrow_change_usd"],
        change_effective=data["change_effective"],
        drivers=data["drivers"],
        last_disbursements=[
            schemas.DisbursementItem(**item) for item in data["last_disbursements"]
        ],
        next_analysis_date=data["next_analysis_date"],
    )


# ── Endpoints ──────────────────────────────────────────────────────────────


@app.get("/tools", response_model=list[str])
async def list_tools(token: str = Depends(verify_token)) -> list[str]:
    """List all available tools."""
    return [
        "lookup_loan",
        "search_borrower",
        "get_payment_schedule",
        "get_escrow_breakdown",
        "check_hardship_eligibility",
        "search_policy",
    ]


@app.post("/tools/lookup_loan", response_model=schemas.LoanSummary)
@app.post("/lookup_loan", response_model=schemas.LoanSummary)
async def lookup_loan(
    request: LookupLoanRequest,
    token: str = Depends(verify_token),
) -> schemas.LoanSummary:
    """Retrieve basic details about a loan."""
    loan = await async_get_loan_or_404(request.loan_id)
    return to_loan_summary(loan)


@app.post("/tools/search_borrower", response_model=list[schemas.LoanSummary])
@app.post("/search_borrower", response_model=list[schemas.LoanSummary])
async def search_borrower(
    request: SearchBorrowerRequest,
    token: str = Depends(verify_token),
) -> list[schemas.LoanSummary]:
    """Search loans by borrower name (case-insensitive partial token match)."""
    matches = await search_loans_by_borrower_name(request.name)
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No loans found for borrower '{request.name}'",
        )

    return matches


@app.post("/tools/get_payment_schedule", response_model=schemas.PaymentSchedule)
@app.post("/get_payment_schedule", response_model=schemas.PaymentSchedule)
async def get_payment_schedule(
    request: GetPaymentScheduleRequest,
    token: str = Depends(verify_token),
) -> schemas.PaymentSchedule:
    """Generate upcoming payment schedule."""
    await async_get_loan_or_404(request.loan_id)
    provider = get_loan_data_provider()
    schedule = await provider.get_payment_schedule(request.loan_id, months=request.months)
    return to_payment_schedule(schedule)


@app.post("/tools/get_escrow_breakdown", response_model=schemas.EscrowBreakdown)
@app.post("/get_escrow_breakdown", response_model=schemas.EscrowBreakdown)
async def get_escrow_breakdown(
    request: GetEscrowBreakdownRequest,
    token: str = Depends(verify_token),
) -> schemas.EscrowBreakdown:
    """Retrieve escrow account breakdown and disbursement history."""
    await async_get_loan_or_404(request.loan_id)
    provider = get_loan_data_provider()
    breakdown = await provider.get_escrow_breakdown(request.loan_id)
    return to_escrow_breakdown(breakdown)


@app.post("/tools/check_hardship_eligibility", response_model=schemas.EligibilityHint)
@app.post("/check_hardship_eligibility", response_model=schemas.EligibilityHint)
async def check_hardship_eligibility(
    request: CheckHardshipEligibilityRequest,
    token: str = Depends(verify_token),
) -> schemas.EligibilityHint:
    """Evaluate hardship program eligibility hints."""
    loan = await async_get_loan_or_404(request.loan_id)
    program = request.program

    # 1. Disaster Forbearance eligibility rules
    if program == "disaster_forbearance":
        # Eligible states in our system
        if loan["state"] in ("CA", "FL"):
            return schemas.EligibilityHint(
                loan_id=request.loan_id,
                program=program,
                hint="likely_eligible",
                reasoning_factors=[
                    f"property_state_in_declared_disaster_area={loan['state']}",
                    f"delinquency_days={loan['delinquency_days']}<=60",
                    "no_active_loss_mit_plan",
                ],
                documentation_required=["FEMA disaster ID", "borrower hardship attestation"],
                binding=False,
                next_step="Route to Loss Mitigation queue for formal eligibility review.",
            )
        else:
            return schemas.EligibilityHint(
                loan_id=request.loan_id,
                program=program,
                hint="unlikely_eligible",
                reasoning_factors=[
                    f"property_state_not_in_declared_disaster_area={loan['state']}",
                ],
                documentation_required=[],
                binding=False,
                next_step=(
                    "Inform borrower of state-specific options or route to General Servicing."
                ),
            )

    # 2. Covid Forbearance eligibility rules
    elif program == "covid_forbearance":
        return schemas.EligibilityHint(
            loan_id=request.loan_id,
            program=program,
            hint="unlikely_eligible",
            reasoning_factors=["national_covid_forbearance_program_expired=2024-06-30"],
            documentation_required=[],
            binding=False,
            next_step="Assess for alternative programs or route to General Servicing.",
        )

    # 3. Repayment Plan eligibility rules
    elif program == "repayment_plan":
        if 0 < loan["delinquency_days"] <= 90:
            return schemas.EligibilityHint(
                loan_id=request.loan_id,
                program=program,
                hint="likely_eligible",
                reasoning_factors=[
                    f"delinquency_days={loan['delinquency_days']}>0",
                    "delinquency_days<=90",
                    "stable_income_attested",
                ],
                documentation_required=["income verification", "hardship explanation letter"],
                binding=False,
                next_step="Route to Loss Mitigation queue for repayment plan setup.",
            )
        else:
            return schemas.EligibilityHint(
                loan_id=request.loan_id,
                program=program,
                hint="unlikely_eligible",
                reasoning_factors=[
                    f"delinquency_days={loan['delinquency_days']} not in range 1-90",
                ],
                documentation_required=[],
                binding=False,
                next_step=("Assess for alternative programs or route to foreclosure prevention."),
            )

    # 4. Fallback for other programs
    return schemas.EligibilityHint(
        loan_id=request.loan_id,
        program=program,
        hint="unlikely_eligible",
        reasoning_factors=[f"program_not_actively_offered={program}"],
        documentation_required=[],
        binding=False,
        next_step="Route to General Servicing.",
    )


@app.post("/tools/search_policy", response_model=schemas.PolicyChunks)
@app.post("/search_policy", response_model=schemas.PolicyChunks)
async def search_policy(
    request: SearchPolicyRequest,
    token: str = Depends(verify_token),
) -> schemas.PolicyChunks:
    """Integrate with RAG providers to query policies."""
    # Obtain embedding and vector store providers via the abstract factory
    try:
        embedder = get_embedding_provider()
        vector_store = get_vector_store_provider()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load RAG providers: {e}",
        ) from e

    # Embed the query
    try:
        embedding_res = await embedder.embed(request.query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embedding: {e}",
        ) from e

    # Re-ranker is opt-in (heavy: sentence-transformers). Skip by default —
    # especially for embedded Qdrant local mode where disk/RAM is constrained.
    reranker = None
    if settings.vector_store.provider == "qdrant" and not settings.vector_store.qdrant.path:
        try:
            from packages.common.providers.factory import get_reranker_provider

            reranker = get_reranker_provider()
            logger.info("Re-ranker enabled for Qdrant vector store")
        except Exception as e:
            logger.warning(f"Re-ranker not available: {e}")
    else:
        logger.info("Re-ranker disabled (embedded Qdrant or AI Search)")

    # Search the vector store
    # Query a larger pool of results to allow robust in-memory filtering by state
    try:
        # Always pass query text for hybrid search (all providers now support it)
        search_kwargs = {
            "embedding": embedding_res.vector,
            "query_text": request.query,  # Hybrid search support
            "top_k": max(request.k * 4, 20),
        }

        search_results = await vector_store.search(**search_kwargs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector store search failed: {e}",
        ) from e

    # Apply local re-ranking if available (for Qdrant)
    if reranker and search_results:
        # Extract document texts
        doc_texts = [r.text or "" for r in search_results]

        # Re-rank documents
        try:
            reranked_results = await reranker.rerank(request.query, doc_texts)

            # Reorder search results based on re-ranking
            reranked_search_results = []
            for rr in reranked_results:
                if rr.index < len(search_results):
                    # Create a new SearchResult with updated score
                    original = search_results[rr.index]
                    result = SearchResult(
                        id=original.id,
                        score=rr.score,
                        metadata=original.metadata,
                        text=original.text,
                    )
                    reranked_search_results.append(result)

            search_results = reranked_search_results
        except Exception as rerank_error:
            # Log error but continue with original results
            logger.error(f"Re-ranking failed: {rerank_error}")
            pass

    # Filter results by state in memory
    filtered = []
    for r in search_results:
        doc_state = r.metadata.get("state")

        # If no state is specified in request, retrieve everything
        if request.state is None:
            filtered.append(r)
        else:
            # If state is specified, match specified state or "national"
            if doc_state == "national" or doc_state == request.state:
                filtered.append(r)

        if len(filtered) >= request.k:
            break

    # Map results to expected output schema
    results = [
        schemas.PolicyResultItem(
            chunk_id=r.id,
            score=r.score,
            snippet=r.text or "",
            source_path=r.metadata.get("source", ""),
            version=r.metadata.get("version", "1.0"),
        )
        for r in filtered
    ]

    return schemas.PolicyChunks(
        query=request.query,
        state=request.state,
        results=results,
    )
