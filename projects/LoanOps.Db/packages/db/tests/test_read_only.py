"""DB read-only classifier tests."""

from packages.db.client import classify_read_only


def test_select_ok() -> None:
    ok, reason = classify_read_only("SELECT TOP 5 * FROM dbo.Loans WHERE Id = 1")
    assert ok
    assert reason is None


def test_delete_rejected() -> None:
    ok, reason = classify_read_only("DELETE FROM dbo.Loans")
    assert not ok
    assert reason is not None


def test_select_into_rejected_via_keyword() -> None:
    ok, reason = classify_read_only("SELECT * INTO dbo.Tmp FROM dbo.Loans")
    assert not ok
