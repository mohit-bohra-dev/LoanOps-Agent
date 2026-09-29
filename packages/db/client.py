"""SQL Server client — fixed servicing queries + read-only ad-hoc SELECT.

Prerequisite: Microsoft ODBC Driver 18 for SQL Server + ``aioodbc``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|CREATE|ALTER|EXEC|EXECUTE|"
    r"MERGE|BULK|GRANT|DENY|REVOKE|INTO)\b",
    re.IGNORECASE,
)
_ALPHANUM = re.compile(r"^[a-zA-Z0-9]+$")


def strip_literals_and_comments(sql: str) -> str:
    sql = re.sub(r"/\*[\s\S]*?\*/", " ", sql)
    sql = re.sub(r"--[^\n\r]*", " ", sql)
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    sql = re.sub(r"\[(?:[^\]]|\])*\]", "[]", sql)
    return sql


def classify_read_only(sql: str) -> tuple[bool, str | None]:
    """Fail-closed keyword net for ad-hoc SQL (AST parser optional later)."""
    stripped = strip_literals_and_comments(sql)
    if _WRITE_KEYWORDS.search(stripped):
        return False, "contains a write/execute keyword"
    if not re.search(r"\bSELECT\b", stripped, re.IGNORECASE):
        return False, "no SELECT to read from"
    return True, None


@dataclass
class DbConfig:
    server: str = ""
    database: str = ""
    user: str = ""
    password: str = ""
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: bool = True
    trust_server_certificate: bool = True


class SqlServerClient:
    """Thin aioodbc wrapper. Fixture mode returns canned rows without ODBC."""

    def __init__(self, config: DbConfig, *, fixture_mode: bool = False) -> None:
        self.config = config
        self.fixture_mode = fixture_mode
        self._conn: Any = None

    def _connection_string(self) -> str:
        parts = [
            f"DRIVER={{{self.config.driver}}}",
            f"SERVER={self.config.server}",
            f"DATABASE={self.config.database}",
            f"UID={self.config.user}",
            f"PWD={self.config.password}",
        ]
        if self.config.encrypt:
            parts.append("Encrypt=yes")
        if self.config.trust_server_certificate:
            parts.append("TrustServerCertificate=yes")
        return ";".join(parts)

    async def _ensure_conn(self) -> Any:
        if self.fixture_mode:
            return None
        if self._conn is not None:
            return self._conn
        try:
            import aioodbc
        except ImportError as exc:
            raise ImportError(
                "aioodbc required for live SQL Server. "
                "Install aioodbc and Microsoft ODBC Driver 18."
            ) from exc
        self._conn = await aioodbc.connect(dsn=self._connection_string(), autocommit=True)
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def get_customer_servicing_summary(self, customer_id: str) -> str:
        if not _ALPHANUM.match(customer_id):
            return "Provided Customer ID violates strict alphanumeric format constraints."
        if self.fixture_mode:
            return (
                f"Data Profile Summary for Customer: {customer_id}\n"
                f"- Date: 2026-09-01 | Status: Current | Balance: $1200.00 | Notes: fixture"
            )
        conn = await self._ensure_conn()
        sql = """
            SELECT TOP 5 RecordDate, AccountStatus, CurrentBalance, AgentNotes
            FROM dbo.SSE_Servicing_Data
            WHERE CustomerID = ?
            ORDER BY RecordDate DESC
        """
        async with conn.cursor() as cur:
            await cur.execute(sql, (customer_id,))
            rows = await cur.fetchall()
        if not rows:
            return (
                f"Query executed successfully. No servicing records located "
                f"for Customer ID: {customer_id}"
            )
        lines = [f"Data Profile Summary for Customer: {customer_id}"]
        for row in rows:
            record_date = str(row[0])[:10]
            lines.append(
                f"- Date: {record_date} | Status: {row[1]} | "
                f"Balance: ${float(row[2]):.2f} | Notes: {row[3]}"
            )
        return "\n".join(lines)

    async def run_read_only_query(self, sql: str, limit: int = 100) -> str:
        ok, reason = classify_read_only(sql)
        if not ok:
            return f"Rejected: {reason}"
        if self.fixture_mode:
            return f"fixture_ok rows=0 (sql accepted, length={len(sql)})"
        conn = await self._ensure_conn()
        wrapped = f"SELECT TOP {int(limit)} * FROM ({sql}) AS _q"
        async with conn.cursor() as cur:
            await cur.execute(sql if "TOP" in sql.upper() else wrapped)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = await cur.fetchall()
        if not rows:
            return "0 rows"
        preview = [dict(zip(columns, row, strict=False)) for row in rows[:20]]
        return str(preview)
