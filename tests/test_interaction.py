"""
Unit tests for interaction endpoint baselines (/v1/tick, /v1/reply).
"""

from fastapi.testclient import TestClient


def test_tick_stub(client: TestClient):
    """Verify /v1/tick returns valid empty actions response for Phase 1."""
    response = client.post(
        "/v1/tick",
        json={
            "now": "2026-04-26T10:30:00Z",
            "available_triggers": ["trg_001_research_digest"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "actions" in data
    assert isinstance(data["actions"], list)


def test_reply_active(client: TestClient):
    """Verify /v1/reply processes affirmative message and returns send action for Phase 3B."""
    response = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_001",
            "merchant_id": "m_001_drmeera",
            "customer_id": None,
            "from_role": "merchant",
            "message": "Yes, send me the details",
            "received_at": "2026-04-26T10:35:00Z",
            "turn_number": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "send"
    assert "rationale" in data

