"""Test the upstream Loan Services API using configured paths only.

Does NOT brute-force endpoints. Set exact paths in .env (or pass flags),
paste Bearer token, then run targeted calls.

Config (.env):
  DATA__LOAN_API__BASE_URL
  DATA__LOAN_API__API_KEY
  DATA__LOAN_API__GET_LOAN_PATH=/api/loans/{loan_id}
  DATA__LOAN_API__SEARCH_PATH=/api/loans/search
  DATA__LOAN_API__SEARCH_QUERY_PARAM=borrowerName

Usage:
  # 1. Paste token into .env, then:
  uv run python scripts/probe_loan_api.py --loan-id 100245
  uv run python scripts/probe_loan_api.py --search "Alex Rivera"

  # 2. Or pass token inline (avoid committing to .env):
  uv run python scripts/probe_loan_api.py --token "eyJ..." --loan-id 100245
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx

from packages.common.settings import Settings


def _mask_token(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


def _preview_body(text: str, limit: int = 1200) -> str:
    text = text.strip()
    if not text:
        return "(empty)"
    try:
        parsed = json.loads(text)
        compact = json.dumps(parsed, indent=2)
        if len(compact) <= limit:
            return compact
        return compact[:limit] + "\n... (truncated)"
    except json.JSONDecodeError:
        if len(text) <= limit:
            return text
        return text[:limit] + "... (truncated)"


def _print_section(title: str) -> None:
    print()
    print("=" * len(title))
    print(title)
    print("=" * len(title))


async def _get(
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
) -> None:
    url = f"{base_url.rstrip('/')}{path}"
    print(f"GET {url}")
    if params:
        print(f"    params: {params}")
    try:
        response = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        print(f"    ERROR: {exc}")
        return

    print(f"    status: {response.status_code}")
    print(f"    type:   {response.headers.get('content-type', '')}")
    print(_preview_body(response.text))


async def run_test(
    *,
    base_url: str,
    token: str,
    timeout_seconds: int,
    get_loan_path: str,
    search_path: str,
    search_query_param: str,
    loan_id: str | None,
    search_query: str | None,
    swagger_path: str | None,
) -> int:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    timeout = httpx.Timeout(timeout_seconds)

    _print_section("Loan API test (configured paths only)")
    print(f"base_url         : {base_url}")
    print(f"token            : {_mask_token(token)}")
    print(f"get_loan_path    : {get_loan_path}")
    print(f"search_path      : {search_path}")
    print(f"search_query_param: {search_query_param}")

    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        if swagger_path:
            _print_section("Swagger / OpenAPI")
            await _get(client, base_url, swagger_path)

        if loan_id:
            _print_section(f"Loan lookup ({loan_id})")
            path = get_loan_path.format(loan_id=loan_id.strip())
            await _get(client, base_url, path)

        if search_query:
            _print_section(f"Borrower search ({search_query!r})")
            path = search_path
            params: dict[str, str] | None = None
            if "{" not in path:
                params = {search_query_param: search_query.strip()}
            else:
                path = path.format(
                    name=search_query.strip(),
                    borrower_name=search_query.strip(),
                    borrowerName=search_query.strip(),
                    query=search_query.strip(),
                )
            await _get(client, base_url, path, params=params)

        if not loan_id and not search_query and not swagger_path:
            print()
            print("Nothing to call. Pass at least one of:")
            print("  --loan-id <id>")
            print("  --search <borrower name>")
            print("  --swagger-path /swagger/v1/swagger.json")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Test Loan Services API using configured paths (no brute-force)"
    )
    parser.add_argument("--loan-id", help="Loan ID for GET_LOAN_PATH")
    parser.add_argument("--search", help="Borrower name for SEARCH_PATH")
    parser.add_argument("--swagger-path", help="Optional swagger/openapi path to fetch")
    parser.add_argument("--base-url", help="Override DATA__LOAN_API__BASE_URL")
    parser.add_argument("--token", help="Bearer token (override DATA__LOAN_API__API_KEY)")
    parser.add_argument("--get-loan-path", help="Override DATA__LOAN_API__GET_LOAN_PATH")
    parser.add_argument("--search-path", help="Override DATA__LOAN_API__SEARCH_PATH")
    parser.add_argument(
        "--search-query-param",
        help="Override DATA__LOAN_API__SEARCH_QUERY_PARAM",
    )
    parser.add_argument("--timeout", type=int, help="HTTP timeout seconds")
    args = parser.parse_args(argv)

    settings = Settings()
    loan_api = settings.data.loan_api
    base_url = args.base_url or loan_api.base_url
    token = args.token or loan_api.api_key
    timeout_seconds = args.timeout or loan_api.timeout_seconds
    get_loan_path = args.get_loan_path or loan_api.get_loan_path
    search_path = args.search_path or loan_api.search_path
    search_query_param = args.search_query_param or loan_api.search_query_param

    if not base_url:
        print("ERROR: Set DATA__LOAN_API__BASE_URL or pass --base-url", file=sys.stderr)
        return 1
    if not token or token.startswith("<"):
        print(
            "ERROR: Paste Bearer token into DATA__LOAN_API__API_KEY or pass --token",
            file=sys.stderr,
        )
        return 1

    import asyncio

    return asyncio.run(
        run_test(
            base_url=base_url,
            token=token,
            timeout_seconds=timeout_seconds,
            get_loan_path=get_loan_path,
            search_path=search_path,
            search_query_param=search_query_param,
            loan_id=args.loan_id,
            search_query=args.search,
            swagger_path=args.swagger_path,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
