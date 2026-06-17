import pytest
from fastapi.testclient import TestClient

from apps.tools_api.main import app
from packages.common.settings import Settings

settings = Settings()
AUTH_HEADERS = {"Authorization": f"Bearer {settings.tools_api_token}"}
INVALID_AUTH_HEADERS = {"Authorization": "Bearer invalid"}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_auth_required(client) -> None:
    """Verify that endpoints reject missing or invalid tokens."""
    response = client.get("/tools")
    assert response.status_code == 401

    response = client.get("/tools", headers=INVALID_AUTH_HEADERS)
    assert response.status_code == 401

    response = client.post("/tools/lookup_loan", json={"loan_id": "100245"})
    assert response.status_code == 401


def test_list_tools(client) -> None:
    """Verify listing tools works with valid token."""
    response = client.get("/tools", headers=AUTH_HEADERS)
    assert response.status_code == 200
    tools = response.json()
    assert isinstance(tools, list)
    assert "lookup_loan" in tools
    assert "search_policy" in tools


def test_lookup_loan_success(client) -> None:
    """Verify details can be retrieved for a valid loan ID."""
    response = client.post(
        "/tools/lookup_loan",
        json={"loan_id": "100245"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["loan_id"] == "100245"
    assert data["borrower_first_name"] == "Alex"
    assert data["state"] == "CA"
    assert data["escrowed"] is True
    assert "last_payment_date" in data


def test_lookup_loan_not_found(client) -> None:
    """Verify 404 is returned for nonexistent loan ID."""
    response = client.post(
        "/tools/lookup_loan",
        json={"loan_id": "999999"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_search_borrower_success(client):
    """Verify search borrower endpoint returns valid results."""
    response = client.post(
        "/tools/search_borrower",
        json={"name": "Alex"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) > 0
    assert "borrower_last_name" in results[0]


def test_search_borrower_not_found(client):
    """Verify 404 is returned for nonexistent borrower name."""
    response = client.post(
        "/tools/search_borrower",
        json={"name": "Nonexistent"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
