"""Loan Data Provider Protocol and Implementations."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from packages.common import schemas

logger = logging.getLogger(__name__)


class AbstractLoanDataProvider(ABC):
    """Protocol for fetching loan data."""

    @abstractmethod
    async def get_loan(self, loan_id: str) -> dict[str, Any] | None:
        """Fetch a specific loan by ID."""
        pass

    @abstractmethod
    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        """Search for loans by borrower name."""
        pass


class JsonFileLoanProvider(AbstractLoanDataProvider):
    """Mock provider that reads from data/loans.json."""

    def __init__(self) -> None:
        self._db: dict[str, dict[str, Any]] = {}
        self._load_loans_db()

    def _load_loans_db(self) -> None:
        paths_to_try = [
            Path("data/loans.json"),
            Path(__file__).parent.parent.parent.parent / "data" / "loans.json",
        ]

        loaded = False
        for path in paths_to_try:
            if path.exists():
                try:
                    with open(path, encoding="utf-8") as f:
                        loans_list = json.load(f)
                        for loan in loans_list:
                            self._db[loan["loan_id"]] = loan
                    loaded = True
                    break
                except Exception as e:
                    logger.error(f"Error loading loans database from {path}: {e}")

        if not loaded:
            logger.warning("WARNING: Loans database (loans.json) could not be loaded!")

    async def get_loan(self, loan_id: str) -> dict[str, Any] | None:
        """Retrieve loan from the local in-memory dict."""
        clean_loan_id = loan_id.strip()
        if not self._db:
            self._load_loans_db()
        return self._db.get(clean_loan_id)

    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        """Search loan records by borrower name in the local database."""
        if not self._db:
            self._load_loans_db()

        query_tokens = [token for token in name.lower().split() if token]
        if not query_tokens:
            return []

        matches: list[dict[str, Any]] = []
        for loan in self._db.values():
            first = loan["borrower_first_name"].lower()
            last = loan["borrower_last_name"].lower()
            full = f"{first} {last}"

            if all(token in first or token in last or token in full for token in query_tokens):
                matches.append(loan)

        return matches[:10]


class RestApiLoanProvider(AbstractLoanDataProvider):
    """Real provider that calls a REST API."""

    def __init__(self, config: Any) -> None:
        self.config = config

    async def get_loan(self, loan_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("Real loan API not yet implemented (waiting for endpoint details)")

    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        raise NotImplementedError("Real loan API not yet implemented (waiting for endpoint details)")
