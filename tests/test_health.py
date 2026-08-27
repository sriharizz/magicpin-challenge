"""
Unit tests for Health (/v1/healthz) and Metadata (/v1/metadata) endpoints.
"""

from fastapi.testclient import TestClient


def test_healthz_initial_state(client: TestClient):
    """Verify healthz returns status: ok, valid uptime, and zero initial counts."""
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
    assert data["contexts_loaded"] == {
        "category": 0,
        "merchant": 0,
        "customer": 0,
        "trigger": 0,
    }


def test_healthz_counts_after_ingestion(client: TestClient):
    """Verify healthz dynamically reflects accurate counts for all scopes."""
    # Push 2 categories
    client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": {}, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "category", "context_id": "salons", "version": 1, "payload": {}, "delivered_at": "2026-04-26T10:00:00Z"})

    # Push 3 merchants
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_001", "version": 1, "payload": {}, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_002", "version": 1, "payload": {}, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_003", "version": 1, "payload": {}, "delivered_at": "2026-04-26T10:00:00Z"})

    # Push 1 customer
    client.post("/v1/context", json={"scope": "customer", "context_id": "c_001", "version": 1, "payload": {}, "delivered_at": "2026-04-26T10:00:00Z"})

    # Push 2 triggers
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_001", "version": 1, "payload": {}, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_002", "version": 1, "payload": {}, "delivered_at": "2026-04-26T10:00:00Z"})

    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["contexts_loaded"] == {
        "category": 2,
        "merchant": 3,
        "customer": 1,
        "trigger": 2,
    }


def test_metadata_endpoint(client: TestClient):
    """Verify metadata endpoint returns all required contract fields."""
    response = client.get("/v1/metadata")
    assert response.status_code == 200
    data = response.json()
    required_keys = [
        "team_name",
        "team_members",
        "model",
        "approach",
        "contact_email",
        "version",
        "submitted_at",
    ]
    for key in required_keys:
        assert key in data
        assert data[key] is not None

    assert isinstance(data["team_members"], list)
    assert len(data["team_members"]) > 0


def test_root_endpoint(client: TestClient):
    """Verify root / returns 200 and lists available endpoints."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "endpoints" in data
    assert len(data["endpoints"]) == 5

