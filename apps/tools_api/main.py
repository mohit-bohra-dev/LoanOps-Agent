from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from provider_contracts.vector_store import SearchResult
from pydantic import BaseModel

from packages.common import schemas
from packages.common.providers.factory import get_embedding_provider, get_vector_store_provider
from packages.common.settings import Settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Servicing Tools API",
    description="Mock servicing API endpoints for the Servicing Agent",
    version="1.0.0",
    redoc_url=None,
)

security = HTTPBearer()
settings = Settings()

# In-memory database loaded from loans.json
LOANS_DB: dict[str, dict[str, Any]] = {}


def load_loans_db() -> None:
    """Load the synthetic loans database from loans.json."""
    # Search in common locations
    paths_to_try = [
        Path("data/loans.json"),
        Path(__file__).parent.parent.parent / "data" / "loans.json",
    ]

    loaded = False
    for path in paths_to_try:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    loans_list = json.load(f)
                    for loan in loans_list:
                        LOANS_DB[loan["loan_id"]] = loan
                loaded = True
                break
            except Exception as e:
                print(f"Error loading loans database from {path}: {e}")

    if not loaded:
        print("WARNING: Loans database (loans.json) could not be loaded!")


@app.on_event("startup")
def startup_event() -> None:
    load_loans_db()


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
    # Strip whitespace to handle LLM formatting quirks
    clean_loan_id = loan_id.strip()

    # Make sure DB is loaded (useful if startup event hasn't run in test context)
    if not LOANS_DB:
        load_loans_db()

    loan = LOANS_DB.get(clean_loan_id)
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
    )


def matches_borrower_name(loan: dict[str, Any], query: str) -> bool:
    """Return True when a case-insensitive borrower name match is found."""
    query_tokens = [token for token in query.lower().split() if token]
    if not query_tokens:
        return False

    first = loan["borrower_first_name"].lower()
    last = loan["borrower_last_name"].lower()
    full = f"{first} {last}"

    return all(token in first or token in last or token in full for token in query_tokens)


def search_loans_by_borrower_name(name: str) -> list[schemas.LoanSummary]:
    """Search loan records by borrower name and return up to 10 matches."""
    if not LOANS_DB:
        load_loans_db()

    matches: list[schemas.LoanSummary] = []
    for loan in LOANS_DB.values():
        if matches_borrower_name(loan, name):
            matches.append(to_loan_summary(loan))

    return matches[:10]


# ── Endpoints ──────────────────────────────────────────────────────────────


@app.get("/")
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
    loan = get_loan_or_404(request.loan_id)
    return to_loan_summary(loan)


@app.post("/tools/search_borrower", response_model=list[schemas.LoanSummary])
@app.post("/search_borrower", response_model=list[schemas.LoanSummary])
async def search_borrower(
    request: SearchBorrowerRequest,
    token: str = Depends(verify_token),
) -> list[schemas.LoanSummary]:
    """Search loans by borrower name (case-insensitive partial token match)."""
    matches = search_loans_by_borrower_name(request.name)
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
    loan = get_loan_or_404(request.loan_id)

    # Handle paid off loans
    if loan["status"] == "paid_off" or loan["next_due_date"] is None:
        return schemas.PaymentSchedule(loan_id=request.loan_id, schedule=[])

    # Match exact example response for 100245
    if request.loan_id == "100245":
        return schemas.PaymentSchedule(
            loan_id=request.loan_id,
            schedule=[
                schemas.PaymentScheduleItem(
                    due_date="2026-06-01",
                    principal=412.55,
                    interest=1180.12,
                    escrow=615.30,
                    total=2207.97,
                ),
                schemas.PaymentScheduleItem(
                    due_date="2026-07-01",
                    principal=413.81,
                    interest=1178.86,
                    escrow=615.30,
                    total=2207.97,
                ),
                schemas.PaymentScheduleItem(
                    due_date="2026-08-01",
                    principal=415.07,
                    interest=1177.60,
                    escrow=615.30,
                    total=2207.97,
                ),
            ][: request.months],
        )

    # Generate schedule dynamically for other loans
    schedule_items: list[schemas.PaymentScheduleItem] = []
    base_date = datetime.strptime(loan["next_due_date"], "%Y-%m-%d")

    balance = loan["current_balance_usd"]
    interest_rate = 0.045  # Default 4.5% interest rate

    # Estimate total P&I payment using standard amortizing mortgage formula
    # Assuming a 30 year (360 month) remaining term for realism
    remaining_months = 360
    monthly_rate = interest_rate / 12

    if monthly_rate > 0:
        total_pi = (
            balance
            * (monthly_rate * (1 + monthly_rate) ** remaining_months)
            / ((1 + monthly_rate) ** remaining_months - 1)
        )
    else:
        total_pi = balance / remaining_months

    total_pi = round(total_pi, 2)
    escrow = 615.30 if loan["escrowed"] else 0.0

    for i in range(request.months):
        # simplified month increment
        due_date_str = (base_date + timedelta(days=30 * i)).strftime("%Y-%m-%d")

        interest = round(balance * interest_rate / 12, 2)
        principal = round(total_pi - interest, 2)

        # Ensure we don't overpay the remaining balance
        if principal > balance:
            principal = round(balance, 2)
            total_pi = round(principal + interest, 2)

        total = round(principal + interest + escrow, 2)

        schedule_items.append(
            schemas.PaymentScheduleItem(
                due_date=due_date_str,
                principal=principal,
                interest=interest,
                escrow=escrow,
                total=total,
            )
        )
        balance = round(balance - principal, 2)
        if balance <= 0:
            break

    return schemas.PaymentSchedule(loan_id=request.loan_id, schedule=schedule_items)


@app.post("/tools/get_escrow_breakdown", response_model=schemas.EscrowBreakdown)
@app.post("/get_escrow_breakdown", response_model=schemas.EscrowBreakdown)
async def get_escrow_breakdown(
    request: GetEscrowBreakdownRequest,
    token: str = Depends(verify_token),
) -> schemas.EscrowBreakdown:
    """Retrieve escrow account breakdown and disbursement history."""
    loan = get_loan_or_404(request.loan_id)

    # Non-escrowed loans
    if not loan["escrowed"]:
        return schemas.EscrowBreakdown(
            loan_id=request.loan_id,
            as_of="2026-04-30",
            escrow_balance_usd=0.0,
            monthly_escrow_usd=0.0,
            monthly_escrow_change_usd=0.0,
            change_effective="",
            drivers=[],
            last_disbursements=[],
            next_analysis_date="",
        )

    # Match exact example response for 100245
    if request.loan_id == "100245":
        return schemas.EscrowBreakdown(
            loan_id=request.loan_id,
            as_of="2026-04-30",
            escrow_balance_usd=1842.10,
            monthly_escrow_usd=615.30,
            monthly_escrow_change_usd=35.12,
            change_effective="2026-05-01",
            drivers=["county_tax_reassessment", "hazard_premium"],
            last_disbursements=[
                schemas.DisbursementItem(
                    date="2026-03-15",
                    type="county_property_tax",
                    amount_usd=3120.00,
                ),
                schemas.DisbursementItem(
                    date="2026-02-01",
                    type="hazard_insurance",
                    amount_usd=1842.00,
                ),
            ],
            next_analysis_date="2027-03-01",
        )

    # Return default deterministic escrow breakdown for other escrowed loans
    return schemas.EscrowBreakdown(
        loan_id=request.loan_id,
        as_of="2026-04-30",
        escrow_balance_usd=1500.00,
        monthly_escrow_usd=500.00,
        monthly_escrow_change_usd=20.00,
        change_effective="2026-05-01",
        drivers=["county_tax_reassessment"],
        last_disbursements=[
            schemas.DisbursementItem(
                date="2026-03-15",
                type="county_property_tax",
                amount_usd=2500.00,
            ),
            schemas.DisbursementItem(
                date="2026-02-01",
                type="hazard_insurance",
                amount_usd=1500.00,
            ),
        ],
        next_analysis_date="2027-03-01",
    )


@app.post("/tools/check_hardship_eligibility", response_model=schemas.EligibilityHint)
@app.post("/check_hardship_eligibility", response_model=schemas.EligibilityHint)
async def check_hardship_eligibility(
    request: CheckHardshipEligibilityRequest,
    token: str = Depends(verify_token),
) -> schemas.EligibilityHint:
    """Evaluate hardship program eligibility hints."""
    loan = get_loan_or_404(request.loan_id)
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

    # Get re-ranker provider if configured for local development
    # Note: AI Search has built-in semantic ranking, so we only need re-ranker for Qdrant
    reranker = None
    if settings.vector_store.provider == "qdrant":
        try:
            from packages.common.providers.factory import get_reranker_provider

            reranker = get_reranker_provider()
            logger.info("Re-ranker enabled for Qdrant vector store")
        except Exception as e:
            # Re-ranker not available, continue without it
            logger.warning(f"Re-ranker not available: {e}")
    else:
        # For Azure AI Search, use built-in semantic ranking
        logger.info("Re-ranker disabled (AI Search provides built-in semantic ranking)")

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
