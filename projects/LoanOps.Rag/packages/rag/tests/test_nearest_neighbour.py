"""Integration tests for nearest-neighbour retrieval."""

from __future__ import annotations

from typing import Any

import pytest
from packages.common.providers.factory import get_embedding_provider, get_vector_store_provider
from packages.rag.chunker import MarkdownChunker
from provider_contracts.vector_store import VectorDocument


@pytest.mark.integration
async def test_nearest_neighbour_retrieval_with_known_queries() -> None:
    """
    Integration test for nearest-neighbour retrieval using 10 known queries.
    Requires vector store to be running (Qdrant or Azure AI Search).
    """
    # Get providers
    embedder = get_embedding_provider()
    vector_store = get_vector_store_provider()

    # Create realistic SOP content for testing
    sop_contents = [
        {
            "title": "Escrow Account Management",
            "content": """
# Escrow Account Management

## Overview

Escrow accounts are established to collect funds for property taxes and insurance premiums.

## Monthly Collection

Borrowers pay 1/12th of the annual escrow obligations each month. The servicer holds
these funds in a non-interest bearing account.

## Annual Analysis

An escrow analysis is conducted annually to ensure the monthly collection amount is sufficient.
If a surplus of more than $50 exists, it must be refunded to the borrower.
If a shortage exists, the borrower may choose to pay it in full or spread it over 12 months.

## Disbursement

Property taxes are paid when due, typically in one or two annual installments.
Insurance premiums are paid at renewal based on invoices received.
""",
            "metadata": {"category": "escrow", "state": "CA"},
        },
        {
            "title": "Late Payment Policies",
            "content": """
# Late Payment Policies

## Grace Period

A 15-day grace period is provided after the due date with no penalty.

## Late Fees

Late fees are assessed beginning on day 16 after the due date:
- Day 16-30: $15 flat fee
- Day 31+: Additional 5% of overdue amount, capped at $50 total

## Late Payment Reporting

Payments received more than 30 days after due date are reported to credit bureaus.
""",
            "metadata": {"category": "payments", "state": "NY"},
        },
        {
            "title": "Loss Mitigation - Short Sale Program",
            "content": """
# Loss Mitigation - Short Sale Program

## Eligibility

Borrowers must demonstrate:
- Financial hardship
- Insufficient income to continue payments
- Property value less than outstanding loan balance

## Documentation Required

- Completed hardship letter
- Financial statement (Form 1003-B)
- Recent pay stubs
- Tax returns (last 2 years)

## Approval Timeline

Initial review: 30 business days
Approval/decline notification: Within 5 business days of final review
""",
            "metadata": {"category": "loss-mitigation", "state": "FL"},
        },
        {
            "title": "Payoff Statement Requests",
            "content": """
# Payoff Statement Requests

## Request Methods

Payoff statements can be requested:
- Online via borrower portal
- Phone at 1-800-PAYOFF
- Written request to servicing department

## Processing Time

Standard processing time is 3 business days.
Rush requests (fee applies) processed in 1 business day.

## Payoff Components

The payoff amount includes:
- Principal balance
- Accrued interest through payoff date
- Unpaid late charges
- Escrow advances (if applicable)
- Payoff processing fee ($75)
""",
            "metadata": {"category": "payoff", "state": "TX"},
        },
        {
            "title": "Bankruptcy Procedures",
            "content": """
# Bankruptcy Procedures

## Proof of Claim Filing

Within 30 days of noticing a bankruptcy filing, the proof of claim must be filed.

## Stay Violation Requests

Requests for relief from automatic stay require:
- Evidence of default
- Lack of adequate protection
- Motion with supporting documentation

## Reaffirmation Agreements

Reaffirmation agreements must be reviewed by legal counsel.
Court approval is required for reaffirmation to be valid.
""",
            "metadata": {"category": "bankruptcy", "state": "OH"},
        },
    ]

    # Process all SOPs
    all_documents: list[VectorDocument] = []
    chunker = MarkdownChunker()

    for i, sop in enumerate(sop_contents):
        content: str = str(sop["content"])
        metadata: dict[str, Any] = sop["metadata"]  # type: ignore
        # Chunk the content
        chunks = chunker.chunk(content, metadata=metadata)

        # Embed and prepare documents
        for chunk in chunks:
            embedding_result = await embedder.embed(chunk.content)
            doc = VectorDocument(
                id=f"test_{i}_{chunk.chunk_id}",
                embedding=embedding_result.vector,
                metadata=chunk.metadata,
                text=chunk.content,
            )
            all_documents.append(doc)

    # Store all documents
    await vector_store.upsert(all_documents)

    # Define 10 known test queries with expected results
    test_queries = [
        {
            "query": "What happens when borrowers make late payments?",
            "expected_category": "payments",
            "keywords": ["grace", "late fee", "penalty"],
        },
        {
            "query": "How are escrow accounts analyzed each year?",
            "expected_category": "escrow",
            "keywords": ["analysis", "annual", "surplus", "shortage"],
        },
        {
            "query": "What documents are needed for a short sale application?",
            "expected_category": "loss-mitigation",
            "keywords": ["hardship", "financial", "statement", "pay stubs"],
        },
        {
            "query": "How much does a payoff statement cost?",
            "expected_category": "payoff",
            "keywords": ["processing", "fee", "cost", "$"],
        },
        {
            "query": "When is the proof of claim filed in bankruptcy?",
            "expected_category": "bankruptcy",
            "keywords": ["proof", "claim", "filing", "30 days"],
        },
        {
            "query": "What is included in the monthly escrow payment?",
            "expected_category": "escrow",
            "keywords": ["taxes", "insurance", "premiums", "property"],
        },
        {
            "query": "Can I get my payoff statement faster?",
            "expected_category": "payoff",
            "keywords": ["rush", "processing", "time", "business day"],
        },
        {
            "query": "What is the maximum late fee allowed?",
            "expected_category": "payments",
            "keywords": ["capped", "$50", "amount"],
        },
        {
            "query": "How does a short sale affect my loan status?",
            "expected_category": "loss-mitigation",
            "keywords": ["eligibility", "approval", "timeline"],
        },
        {
            "query": "Are escrow funds interest bearing?",
            "expected_category": "escrow",
            "keywords": ["interest", "bearing", "account"],
        },
    ]

    # Test each query
    successful_matches = 0
    total_queries = len(test_queries)

    for test_item in test_queries:
        query: str = str(test_item["query"])
        expected_category = test_item["expected_category"]
        keywords = test_item["keywords"]

        # Embed the query
        query_embedding_result = await embedder.embed(query)

        # Search for similar documents
        results = await vector_store.search(
            embedding=query_embedding_result.vector, top_k=3, min_score=0.1
        )

        # Check if any result matches expected category or contains keywords
        match_found = False
        if results:
            for result in results[:2]:  # Check top 2 results
                # Check metadata category
                text_content = result.text or ""
                if result.metadata.get("category") == expected_category or any(
                    keyword.lower() in text_content.lower() for keyword in keywords
                ):
                    match_found = True
                    break

        if match_found:
            successful_matches += 1

    # Assert that majority of queries return relevant results
    # With 10 queries, we expect at least 7 to return relevant results
    assert successful_matches >= 7, (
        f"Only {successful_matches}/{total_queries} queries returned relevant results"
    )

    # Clean up by deleting the test documents
    await vector_store.delete([doc.id for doc in all_documents])
