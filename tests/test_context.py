"""
Unit tests for Context Ingestion (/v1/context) and SQLite versioning logic.
"""

from fastapi.testclient import TestClient


def test_context_creation_all_four_scopes(client: TestClient):
    """Verify first-version context creation succeeds across category, merchant, customer, and trigger scopes."""
    scopes_data = [
        ("category", "dentists", 1, {"slug": "dentists", "voice": {"tone": "peer_clinical"}}),
        ("merchant", "m_001_drmeera", 1, {"merchant_id": "m_001_drmeera", "identity": {"name": "Dr. Meera"}}),
        ("customer", "c_001_priya", 1, {"customer_id": "c_001_priya", "identity": {"name": "Priya"}}),
        ("trigger", "trg_001_digest", 1, {"id": "trg_001_digest", "kind": "research_digest"}),
    ]

    for scope, cid, version, payload in scopes_data:
        response = client.post(
            "/v1/context",
            json={
                "scope": scope,
                "context_id": cid,
                "version": version,
                "payload": payload,
                "delivered_at": "2026-04-26T10:00:00Z",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        assert data["ack_id"] == f"ack_{cid}_v{version}"
        assert "stored_at" in data


def test_duplicate_version_idempotent_noop(client: TestClient):
    """Verify posting the same version again is an idempotent no-op (accepted: true, HTTP 200)."""
    payload = {"merchant_id": "m_001_drmeera", "views": 2400}

    # 1. First push
    res1 = client.post(
        "/v1/context",
        json={
            "scope": "merchant",
            "context_id": "m_001_drmeera",
            "version": 1,
            "payload": payload,
            "delivered_at": "2026-04-26T10:00:00Z",
        },
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["accepted"] is True
    first_stored_at = data1["stored_at"]

    # 2. Duplicate push (same version 1)
    res2 = client.post(
        "/v1/context",
        json={
            "scope": "merchant",
            "context_id": "m_001_drmeera",
            "version": 1,
            "payload": payload,
            "delivered_at": "2026-04-26T10:05:00Z",
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["accepted"] is True
    assert data2["ack_id"] == "ack_m_001_drmeera_v1"
    # Idempotent no-op preserves original storage timestamp
    assert data2["stored_at"] == first_stored_at


def test_higher_version_replacement(client: TestClient):
    """Verify posting a higher version atomically replaces the prior version."""
    # 1. Version 1
    res1 = client.post(
        "/v1/context",
        json={
            "scope": "merchant",
            "context_id": "m_001_drmeera",
            "version": 1,
            "payload": {"views": 2400},
            "delivered_at": "2026-04-26T10:00:00Z",
        },
    )
    assert res1.status_code == 200
    assert res1.json()["accepted"] is True

    # 2. Version 2
    res2 = client.post(
        "/v1/context",
        json={
            "scope": "merchant",
            "context_id": "m_001_drmeera",
            "version": 2,
            "payload": {"views": 2580},
            "delivered_at": "2026-04-26T10:15:00Z",
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["accepted"] is True
    assert data2["ack_id"] == "ack_m_001_drmeera_v2"


def test_stale_version_rejection(client: TestClient):
    """Verify posting a strictly lower version is rejected with HTTP 409 and stale_version reason."""
    # 1. Set current version to 3
    res_v3 = client.post(
        "/v1/context",
        json={
            "scope": "category",
            "context_id": "dentists",
            "version": 3,
            "payload": {"slug": "dentists", "v": 3},
            "delivered_at": "2026-04-26T10:00:00Z",
        },
    )
    assert res_v3.status_code == 200

    # 2. Attempt pushing stale version 1
    res_stale1 = client.post(
        "/v1/context",
        json={
            "scope": "category",
            "context_id": "dentists",
            "version": 1,
            "payload": {"slug": "dentists", "v": 1},
            "delivered_at": "2026-04-26T10:05:00Z",
        },
    )
    assert res_stale1.status_code == 409
    data_stale1 = res_stale1.json()
    assert data_stale1["accepted"] is False
    assert data_stale1["reason"] == "stale_version"
    assert data_stale1["current_version"] == 3

    # 3. Attempt pushing stale version 2
    res_stale2 = client.post(
        "/v1/context",
        json={
            "scope": "category",
            "context_id": "dentists",
            "version": 2,
            "payload": {"slug": "dentists", "v": 2},
            "delivered_at": "2026-04-26T10:10:00Z",
        },
    )
    assert res_stale2.status_code == 409
    data_stale2 = res_stale2.json()
    assert data_stale2["accepted"] is False
    assert data_stale2["reason"] == "stale_version"
    assert data_stale2["current_version"] == 3


def test_invalid_scope_rejection(client: TestClient):
    """Verify invalid scope values are rejected with HTTP 400."""
    response = client.post(
        "/v1/context",
        json={
            "scope": "invalid_unknown_scope",
            "context_id": "ctx_999",
            "version": 1,
            "payload": {},
            "delivered_at": "2026-04-26T10:00:00Z",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["accepted"] is False
    assert data["reason"] == "invalid_scope"


def test_missing_fields_validation_rejection(client: TestClient):
    """Verify missing required fields in context payload are rejected with HTTP 400 and malformed_request."""
    response = client.post(
        "/v1/context",
        json={
            "scope": "merchant",
            # missing context_id
            "version": 1,
            "payload": {},
            "delivered_at": "2026-04-26T10:00:00Z",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["accepted"] is False
    assert data["reason"] == "malformed_request"


def test_context_content_atomic_update_verification(client: TestClient, temp_db_store):
    """Verify that updating to a higher version genuinely updates the stored payload."""
    # 1. Post v1
    client.post(
        "/v1/context",
        json={
            "scope": "merchant",
            "context_id": "m_test_update",
            "version": 1,
            "payload": {"name": "Old Name", "ctr": 0.015},
            "delivered_at": "2026-04-26T10:00:00Z",
        },
    )
    ctx_v1 = temp_db_store.get_context("merchant", "m_test_update")
    assert ctx_v1 is not None
    assert ctx_v1["version"] == 1
    assert ctx_v1["payload"]["name"] == "Old Name"
    assert ctx_v1["payload"]["ctr"] == 0.015

    # 2. Post v2
    client.post(
        "/v1/context",
        json={
            "scope": "merchant",
            "context_id": "m_test_update",
            "version": 2,
            "payload": {"name": "New Name", "ctr": 0.028},
            "delivered_at": "2026-04-26T10:10:00Z",
        },
    )
    ctx_v2 = temp_db_store.get_context("merchant", "m_test_update")
    assert ctx_v2 is not None
    assert ctx_v2["version"] == 2
    assert ctx_v2["payload"]["name"] == "New Name"
    assert ctx_v2["payload"]["ctr"] == 0.028

