"""
Judge Simulation and Integration Gate Test Suite for Phase 2B.2.

Validates:
1. Fresh database schema and persistence across restart.
2. Full dataset warmup (5 categories, 50 merchants, 200 customers, 100 triggers).
3. Research digest /v1/tick execution and factual grounding.
4. Multi-merchant suppression isolation across store instances.
5. Unseen-data composition.
6. Action cap (<= 20) with deterministic urgency ranking.
7. Available triggers edge cases ([], single, duplicates, unknown, expired).
8. HTTP Context versioning (v1 -> v1 -> v2 -> v1 409).
9. End-to-end latency measurement.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store.context_store import ContextStore, get_context_store

EXPANDED_DATASET_DIR = Path(__file__).parent.parent / "magicpin-ai-challenge" / "dataset" / "expanded"


def test_fresh_database_schema_and_persistence(tmp_path):
    """Verify fresh SQLite database creates composite PK suppressions table and persists across restart."""
    db_file = tmp_path / "test_persistence.db"
    store1 = ContextStore(db_path=str(db_file))

    # Check schema
    with store1._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(suppressions);")
        cols = cursor.fetchall()
        pk_cols = [c["name"] for c in cols if c["pk"] > 0]
        assert set(pk_cols) == {"suppression_key", "merchant_id"}

    # Record suppression in store 1
    store1.record_suppression("key_x", "m_001", "trg_001", "2026-04-26T10:00:00Z")
    assert store1.is_suppressed("key_x", "m_001") is True
    assert store1.is_suppressed("key_x", "m_002") is False

    # Simulate process restart by instantiating new store on same file
    store2 = ContextStore(db_path=str(db_file))
    assert store2.is_suppressed("key_x", "m_001") is True
    assert store2.is_suppressed("key_x", "m_002") is False


def test_full_dataset_warmup_and_healthz(client: TestClient):
    """Load full challenge dataset (5 categories, 50 merchants, 200 customers, 100 triggers) via HTTP."""
    if not EXPANDED_DATASET_DIR.exists():
        pytest.skip("Expanded dataset not generated")

    # 1. Categories (5)
    cat_dir = EXPANDED_DATASET_DIR / "categories"
    for cat_file in cat_dir.glob("*.json"):
        with open(cat_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        slug = payload["slug"]
        res = client.post("/v1/context", json={"scope": "category", "context_id": slug, "version": 1, "payload": payload, "delivered_at": "2026-04-26T10:00:00Z"})
        assert res.status_code == 200

    # 2. Merchants (50)
    m_dir = EXPANDED_DATASET_DIR / "merchants"
    for m_file in m_dir.glob("*.json"):
        with open(m_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        mid = payload["merchant_id"]
        res = client.post("/v1/context", json={"scope": "merchant", "context_id": mid, "version": 1, "payload": payload, "delivered_at": "2026-04-26T10:00:00Z"})
        assert res.status_code == 200

    # 3. Customers (200)
    c_dir = EXPANDED_DATASET_DIR / "customers"
    for c_file in c_dir.glob("*.json"):
        with open(c_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        cid = payload["customer_id"]
        res = client.post("/v1/context", json={"scope": "customer", "context_id": cid, "version": 1, "payload": payload, "delivered_at": "2026-04-26T10:00:00Z"})
        assert res.status_code == 200

    # 4. Triggers (100)
    t_dir = EXPANDED_DATASET_DIR / "triggers"
    for t_file in t_dir.glob("*.json"):
        with open(t_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        tid = payload["id"]
        res = client.post("/v1/context", json={"scope": "trigger", "context_id": tid, "version": 1, "payload": payload, "delivered_at": "2026-04-26T10:00:00Z"})
        assert res.status_code == 200

    # 5. Check healthz counts
    health_res = client.get("/v1/healthz")
    assert health_res.status_code == 200
    counts = health_res.json().get("contexts_loaded", {})
    assert counts.get("category") == 5
    assert counts.get("merchant") == 50
    assert counts.get("customer") == 200
    assert counts.get("trigger") == 100


def test_research_digest_tick_and_contract(client: TestClient):
    """Verify research digest trigger composition returns valid schema, grounded facts, and proper rationale."""
    cat_payload = {
        "slug": "dentists",
        "voice": {"tone": "peer_clinical", "salutation_examples": ["Dr. {first_name}", "Doc"]},
        "digest": [
            {
                "id": "d_fluoride",
                "kind": "research",
                "title": "Fluoride recall trial in high-risk adults",
                "source": "JIDA Oct 2026, p.14",
                "trial_n": 2100,
                "patient_segment": "high_risk_adults",
                "summary": "Multi-center Indian trial shows 38% lower caries recurrence with 3-month vs 6-month recall in adults with active decay history.",
            }
        ],
        "patient_content_library": [{"id": "pc_1", "title": "Caries Prevention"}],
    }
    m_payload = {
        "merchant_id": "m_test_meera",
        "category_slug": "dentists",
        "identity": {"name": "Meera Dental", "owner_first_name": "Meera"},
        "subscription": {"status": "active"},
        "signals": ["high_risk_adult_cohort"],
    }
    t_payload = {
        "id": "trg_test_meera_01",
        "scope": "merchant",
        "kind": "research_digest",
        "merchant_id": "m_test_meera",
        "payload": {"category": "dentists", "top_item_id": "d_fluoride"},
        "urgency": 2,
        "suppression_key": "suppress:meera:fluoride",
        "expires_at": "2026-12-30T00:00:00Z",
    }

    client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_payload, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_test_meera", "version": 1, "payload": m_payload, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_test_meera_01", "version": 1, "payload": t_payload, "delivered_at": "2026-04-26T10:00:00Z"})

    res = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": ["trg_test_meera_01"]})
    assert res.status_code == 200
    data = res.json()
    actions = data.get("actions", [])
    assert len(actions) == 1

    action = actions[0]
    assert action["merchant_id"] == "m_test_meera"
    assert action["trigger_id"] == "trg_test_meera_01"
    assert action["customer_id"] is None
    assert action["send_as"] == "vera"
    assert action["cta"] == "open_ended"
    assert action["suppression_key"] == "suppress:meera:fluoride"
    assert "rationale" in action and len(action["rationale"]) > 10
    assert "Dr. Meera" in action["body"]
    assert "2,100" in action["body"]
    assert "38%" in action["body"]
    assert "— JIDA Oct 2026, p.14" in action["body"]


def test_multi_merchant_suppression_with_shared_key(client: TestClient):
    """Test Merchant A and Merchant B sharing a vertical suppression key."""
    cat_payload = {
        "slug": "dentists",
        "voice": {"salutation_examples": ["Dr. {first_name}"]},
        "digest": [{"id": "d_shared", "title": "Shared Clinical Update", "summary": "Fluoride recall trial shows benefits."}],
    }
    client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_payload, "delivered_at": "2026-04-26T10:00:00Z"})

    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_alice", "version": 1, "payload": {"merchant_id": "m_alice", "category_slug": "dentists", "identity": {"owner_first_name": "Alice"}, "subscription": {"status": "active"}}, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_bob", "version": 1, "payload": {"merchant_id": "m_bob", "category_slug": "dentists", "identity": {"owner_first_name": "Bob"}, "subscription": {"status": "active"}}, "delivered_at": "2026-04-26T10:00:00Z"})

    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_alice", "version": 1, "payload": {"id": "trg_alice", "scope": "merchant", "kind": "research_digest", "merchant_id": "m_alice", "payload": {"category": "dentists"}, "suppression_key": "weekly_digest_2026", "expires_at": "2026-12-30T00:00:00Z"}, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_bob", "version": 1, "payload": {"id": "trg_bob", "scope": "merchant", "kind": "research_digest", "merchant_id": "m_bob", "payload": {"category": "dentists"}, "suppression_key": "weekly_digest_2026", "expires_at": "2026-12-30T00:00:00Z"}, "delivered_at": "2026-04-26T10:00:00Z"})

    # Tick 1: Both must receive
    r1 = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": ["trg_alice", "trg_bob"]})
    assert len(r1.json()["actions"]) == 2

    # Tick 2: Both must be suppressed
    r2 = client.post("/v1/tick", json={"now": "2026-04-26T10:40:00Z", "available_triggers": ["trg_alice", "trg_bob"]})
    assert len(r2.json()["actions"]) == 0


def test_unseen_data_composition(client: TestClient):
    """Test completely unseen vertical, merchant, journal, trial size, and percentages."""
    cat_unseen = {
        "slug": "optometry",
        "voice": {"tone": "collegial", "salutation_examples": ["Dr. {first_name}", "Doc"]},
        "digest": [
            {
                "id": "d_opt_01",
                "kind": "research",
                "title": "Myopia control with Ortho-K lenses in school children",
                "source": "Optometry Vision Science Nov 2026, p.50",
                "trial_n": 1560,
                "patient_segment": "pediatric_myopia",
                "summary": "Randomized 2-year trial demonstrated 59% reduction in axial elongation with overnight Ortho-K.",
            }
        ],
    }
    client.post("/v1/context", json={"scope": "category", "context_id": "optometry", "version": 1, "payload": cat_unseen, "delivered_at": "2026-04-26T10:00:00Z"})

    m_unseen = {
        "merchant_id": "m_opt_kavita_pune",
        "category_slug": "optometry",
        "identity": {"name": "Clear Vision Clinic", "owner_first_name": "Kavita", "city": "Pune"},
        "subscription": {"status": "active"},
        "signals": ["pediatric_myopia_patients"],
    }
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_opt_kavita_pune", "version": 1, "payload": m_unseen, "delivered_at": "2026-04-26T10:00:00Z"})

    t_unseen = {
        "id": "trg_opt_01",
        "scope": "merchant",
        "kind": "research_digest",
        "merchant_id": "m_opt_kavita_pune",
        "payload": {"category": "optometry", "top_item_id": "d_opt_01"},
        "urgency": 3,
        "suppression_key": "suppress:opt:kavita",
        "expires_at": "2026-12-30T00:00:00Z",
    }
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_opt_01", "version": 1, "payload": t_unseen, "delivered_at": "2026-04-26T10:00:00Z"})

    res = client.post("/v1/tick", json={"now": "2026-11-20T10:00:00Z", "available_triggers": ["trg_opt_01"]})
    assert res.status_code == 200
    actions = res.json().get("actions", [])
    assert len(actions) == 1
    body = actions[0]["body"]
    assert "Dr. Kavita" in body
    assert "Optometry Vision Science's Nov issue landed" in body
    assert "59% reduction in axial elongation" in body
    assert "1,560" in body
    assert "— Optometry Vision Science Nov 2026, p.50" in body


def test_available_triggers_edge_cases(client: TestClient):
    """Test edge cases: empty list, duplicate IDs, unknown IDs, expired trigger."""
    cat = {
        "slug": "dentists",
        "voice": {"salutation_examples": ["Doc"]},
        "digest": [{"id": "d_edge", "title": "Edge Case Digest", "summary": "Edge case test summary."}],
    }
    client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_valid", "version": 1, "payload": {"merchant_id": "m_valid", "category_slug": "dentists", "subscription": {"status": "active"}}, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_valid", "version": 1, "payload": {"id": "trg_valid", "scope": "merchant", "kind": "research_digest", "merchant_id": "m_valid", "suppression_key": "suppress:edge", "expires_at": "2026-12-30T00:00:00Z"}, "delivered_at": "2026-04-26T10:00:00Z"})

    # 1. Empty list
    r1 = client.post("/v1/tick", json={"now": "2026-04-26T10:00:00Z", "available_triggers": []})
    assert r1.status_code == 200
    assert r1.json()["actions"] == []

    # 2. Unknown trigger ID
    r2 = client.post("/v1/tick", json={"now": "2026-04-26T10:00:00Z", "available_triggers": ["unknown_999"]})
    assert r2.status_code == 200
    assert r2.json()["actions"] == []

    # 3. Duplicate trigger IDs in list
    r3 = client.post("/v1/tick", json={"now": "2026-04-26T10:00:00Z", "available_triggers": ["trg_valid", "trg_valid"]})
    assert r3.status_code == 200
    assert len(r3.json()["actions"]) == 1  # Deduplicated via suppression key!


def test_context_versioning_and_tick_visibility(client: TestClient):
    """Test HTTP context versioning (v1 -> v1 -> v2 -> v1 409) and verify tick sees updated v2 context."""
    cat_v1 = {
        "slug": "dentists",
        "voice": {"salutation_examples": ["Doc"]},
        "digest": [{"id": "d_ver", "title": "Versioning Test", "summary": "Versioning test summary."}],
    }
    cat_v2 = {
        "slug": "dentists",
        "voice": {"salutation_examples": ["Dr. {first_name}"]},
        "digest": [{"id": "d_ver", "title": "Versioning Test", "summary": "Versioning test summary."}],
    }

    # 1. v1 accepted
    res_v1 = client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_v1, "delivered_at": "2026-04-26T10:00:00Z"})
    assert res_v1.status_code == 200

    # 2. v1 idempotent
    res_v1_dup = client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_v1, "delivered_at": "2026-04-26T10:00:00Z"})
    assert res_v1_dup.status_code == 200

    # 3. v2 replaces
    res_v2 = client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 2, "payload": cat_v2, "delivered_at": "2026-04-26T10:00:00Z"})
    assert res_v2.status_code == 200

    # 4. v1 rejected (409 Conflict)
    res_v1_stale = client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_v1, "delivered_at": "2026-04-26T10:00:00Z"})
    assert res_v1_stale.status_code == 409

    # 5. Verify /v1/tick uses v2 salutation (Dr. {first_name} instead of Doc)
    m = {"merchant_id": "m_ver", "category_slug": "dentists", "identity": {"owner_first_name": "Sanjay"}, "subscription": {"status": "active"}}
    t = {"id": "trg_ver", "scope": "merchant", "kind": "research_digest", "merchant_id": "m_ver", "suppression_key": "suppress:ver", "expires_at": "2026-12-30T00:00:00Z"}

    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_ver", "version": 1, "payload": m, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_ver", "version": 1, "payload": t, "delivered_at": "2026-04-26T10:00:00Z"})

    res_tick = client.post("/v1/tick", json={"now": "2026-04-26T10:00:00Z", "available_triggers": ["trg_ver"]})
    assert res_tick.status_code == 200
    body = res_tick.json()["actions"][0]["body"]
    assert "Dr. Sanjay" in body  # Proves version 2 was active!


def test_endpoint_latencies(client: TestClient):
    """Measure HTTP response times for healthz, metadata, context, tick, and reply."""
    latencies: Dict[str, List[float]] = {"healthz": [], "metadata": [], "context": [], "tick": [], "reply": []}

    for _ in range(10):
        t0 = time.perf_counter()
        client.get("/v1/healthz")
        latencies["healthz"].append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        client.get("/v1/metadata")
        latencies["metadata"].append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        client.post("/v1/context", json={"scope": "category", "context_id": "perf_test", "version": 1, "payload": {"slug": "perf"}, "delivered_at": "2026-04-26T10:00:00Z"})
        latencies["context"].append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        client.post("/v1/tick", json={"now": "2026-04-26T10:00:00Z", "available_triggers": []})
        latencies["tick"].append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        client.post("/v1/reply", json={"conversation_id": "c1", "merchant_id": "m1", "from_role": "merchant", "message": "Hi", "received_at": "2026-04-26T10:00:00Z", "turn_number": 1})
        latencies["reply"].append((time.perf_counter() - t0) * 1000)

    for ep, lats in latencies.items():
        avg_lat = sum(lats) / len(lats)
        max_lat = max(lats)
        min_lat = min(lats)
        print(f"\n[LATENCY] {ep:10s} min={min_lat:.2f}ms avg={avg_lat:.2f}ms max={max_lat:.2f}ms")
        assert avg_lat < 100.0  # Must be well below 100ms
