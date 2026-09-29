"""Scopes allow-list tests."""

from packages.common.scopes import tools_for_role, tools_for_scopes


def test_system_has_sse_docs_and_db() -> None:
    tools = tools_for_role("system")
    assert "search_sse_apis" in tools
    assert "search_docs" in tools
    assert "get_customer_servicing_summary" in tools
    assert "wiki_document_feature" not in tools
    assert "lookup_loan" not in tools


def test_customer_blocked_from_wiki() -> None:
    tools = tools_for_role("customer")
    assert "search_sse_apis" in tools
    assert "wiki_search_gitlab" not in tools
    assert "lookup_loan" not in tools


def test_dev_has_wiki() -> None:
    tools = tools_for_scopes(["wiki.gitlab", "sse.read"])
    assert "wiki_search_gitlab" in tools
    assert "call_sse_api" in tools
