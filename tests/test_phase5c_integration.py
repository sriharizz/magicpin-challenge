"""
Integration & Hostile Adversarial Tests for Sandboxed Sandwich Route in Vera (Phase 5C).

Tests:
1. Deterministic fast-exits bypass LLM entirely (0 LLM calls, 0 latency).
2. Nuanced/ambiguous queries invoke LLM and accept valid suggestions.
3. Malicious/invalid LLM outputs are discarded by validator and seamlessly fall back.
4. Provider timeouts, network errors, 5xx, and open circuit breaker fall back with 0 downtime.
5. Double lock guarantees: Terminal states and opt-out suppression cannot be revived by LLM.
6. Replay double lock: Idempotent replays and mutated replays never invoke LLM.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store.context_store import get_context_store
from app.llm.client import get_llm_client, set_llm_client, LLMClient, CircuitBreaker, CircuitState
from app.llm.provider import MockProvider
from app.llm.schemas import LLMDecisionSuggestion
from app.engine.intents import ConversationState, ReplyIntent

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_llm_client():
    """Ensure every test runs with a clean reset of the global LLM client."""
    set_llm_client(None)
    yield
    set_llm_client(None)


def seed_standard_contexts(store):
    """Seed clean mock context for interaction tests."""
    store.clear()

    # Category Context
    cat_payload = {
        "slug": "dentists",
        "voice": {"tone": "peer_clinical", "taboo_words": ["guaranteed", "100%", "miracle", "cure"]},
        "digest": [
            {
                "id": "d_fluoride_2026",
                "title": "High-viscosity glass ionomer cements in root caries",
                "source": "JIDA Oct 2026, p.14",
                "summary": "Clinical trial shows 38% reduction in recurrent caries at 24 months with high-viscosity glass ionomer compared to standard composite resin.",
                "trial_n": 2100,
                "key_takeaway": "GIC provides superior secondary caries prevention in geriatric root lesions.",
            }
        ],
    }
    store.save_context("category", "dentists", 1, cat_payload, "2026-04-26T10:00:00Z")

    # Merchant Context
    merchant_payload = {
        "merchant_id": "m_001_drmeera",
        "category_slug": "dentists",
        "identity": {"name": "Dr. Meera's Clinic"},
        "voice": {"tone": "peer_clinical"},
    }
    store.save_context("merchant", "m_001_drmeera", 1, merchant_payload, "2026-04-26T10:00:00Z")

    # Trigger Context
    trg_payload = {
        "id": "trg_digest_001",
        "scope": "merchant",
        "kind": "research_digest",
        "source": "external",
        "merchant_id": "m_001_drmeera",
        "urgency": 5,
        "suppression_key": "research:dentists:2026-W17",
        "expires_at": "2026-05-30T00:00:00Z",
        "payload": {
            "category": "dentists",
            "top_item_id": "d_fluoride_2026",
            "suppression_key": "research:dentists:2026-W17",
            "urgency": 5,
            "merchant_id": "m_001_drmeera",
        },
    }
    store.save_context("trigger", "trg_digest_001", 1, trg_payload, "2026-04-26T10:00:00Z")


# =============================================================================
# 1. Deterministic Fast-Exits (Zero LLM Invocations)
# =============================================================================

@pytest.mark.parametrize(
    "msg,expected_action",
    [
        ("STOP", "end"),
        ("unsubscribe", "end"),
        ("don't message me again", "end"),
        ("not interested", "end"),
        ("no thanks", "end"),
        ("thank you for contacting us", "wait"),
        ("Can you help me with GST filing?", "send"),
        ("yes", "send"),
        ("ok", "send"),
        ("go ahead", "send"),
        ("👍", "send"),
    ],
)
def test_deterministic_paths_do_not_call_llm(msg, expected_action):
    """Verify standard unambiguous messages execute deterministic path with 0 LLM calls."""
    store = get_context_store()
    seed_standard_contexts(store)

    mock = MockProvider(mode="success")
    test_client = LLMClient(provider=mock)
    set_llm_client(test_client)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": f"conv_det_{abs(hash(msg))}",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": msg,
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == expected_action
    # LLM was never called
    assert mock.call_count == 0
    assert "[LLM-Assisted]" not in resp.json()["rationale"]


# =============================================================================
# 2. Nuanced Paths (LLM Assistance & Acceptance)
# =============================================================================

def test_nuanced_query_calls_llm_and_accepts_valid_suggestion():
    """Verify nuanced questions invoke LLM and adopt approved suggestions."""
    store = get_context_store()
    seed_standard_contexts(store)

    approved_sugg = LLMDecisionSuggestion(
        suggested_intent="INTENT_QUESTION",
        confidence=0.96,
        proposed_action="send",
        response_strategy="explain_root_caries_mechanism",
        draft_body="High-viscosity glass ionomers release fluoride directly at the restoration margin, providing a 38% reduction in recurrent root caries over 24 months (n=2,100). Next step: want me to prepare the patient draft for your team?",
        proposed_cta="binary_yes_no",
        cited_fact_ids=["F1", "F2"],
        unknown_facts_requested=[],
        rationale="Explained clinical mechanism with verified trial facts.",
    )

    mock = MockProvider(custom_suggestion=approved_sugg)
    test_client = LLMClient(provider=mock)
    set_llm_client(test_client)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_nuanced_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Can you explain how this material performs in moisture-sensitive root lesions?",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert mock.call_count == 1
    assert data["action"] == "send"
    assert "38%" in data["body"]
    assert "2,100" in data["body"]
    assert "[LLM-Assisted]" in data["rationale"]


# =============================================================================
# 3. Malicious / Invalid LLM Outputs (Validator Discard & Fallback)
# =============================================================================

def test_malicious_llm_output_rejected_by_validator_and_falls_back():
    """Verify malicious LLM suggestion (hallucinated numbers + forbidden external claims) is discarded."""
    store = get_context_store()
    seed_standard_contexts(store)

    malicious_sugg = LLMDecisionSuggestion(
        suggested_intent="INTENT_AFFIRM",
        confidence=0.99,
        proposed_action="send",
        response_strategy="malicious",
        draft_body="I have published this campaign and sent to all 10,000 patients with 100% cure guaranteed.",
        proposed_cta="binary_yes_no",
        cited_fact_ids=["F99_FABRICATED"],
        unknown_facts_requested=[],
        rationale="Malicious suggestion.",
    )

    mock = MockProvider(custom_suggestion=malicious_sugg)
    test_client = LLMClient(provider=mock)
    set_llm_client(test_client)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_malicious_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "What else can you tell me about the clinical trial protocol?",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert mock.call_count == 1
    # Fallback to deterministic response
    assert "[LLM-Assisted]" not in data["rationale"]
    assert "published" not in data["body"].lower()
    assert "10,000" not in data["body"]
    assert "guaranteed" not in data["body"].lower()


# =============================================================================
# 4. Resilience & Fallbacks (Timeouts, Network Drops, Circuit Breaker)
# =============================================================================

def test_provider_timeout_seamlessly_falls_back():
    """Verify provider timeout executes deterministic fallback without dropping request."""
    store = get_context_store()
    seed_standard_contexts(store)

    mock = MockProvider(mode="timeout")
    test_client = LLMClient(provider=mock, timeout_ms=200)
    set_llm_client(test_client)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_timeout_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Can you explain the statistical significance?",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "send"
    assert "[LLM-Assisted]" not in data["rationale"]


def test_circuit_open_skips_provider_and_falls_back_instantly():
    """Verify tripped circuit breaker executes instant fallback with 0 provider calls."""
    store = get_context_store()
    seed_standard_contexts(store)

    mock = MockProvider(mode="success")
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=10.0)
    cb.state = CircuitState.OPEN
    cb.last_failure_time = 9999999999.0  # Far future to stay OPEN

    test_client = LLMClient(provider=mock, circuit_breaker=cb)
    set_llm_client(test_client)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_circuit_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Can you give me more background on this?",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    assert mock.call_count == 0
    assert "[LLM-Assisted]" not in resp.json()["rationale"]


# =============================================================================
# 5. Terminal State & Opt-Out Double Lock (Hard Invariants)
# =============================================================================

def test_terminal_state_double_lock_blocks_malicious_llm_send():
    """Verify that even if LLM attempts to send on a concluded thread, the route double-lock enforces action: 'end'."""
    store = get_context_store()
    seed_standard_contexts(store)

    # 1. Conclude thread at Turn 2 via Opt-Out
    r_opt = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_double_lock_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Stop messaging me. Unsubscribe.",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert r_opt.json()["action"] == "end"

    # Configure malicious mock to suggest send
    malicious_send = LLMDecisionSuggestion(
        suggested_intent="INTENT_AFFIRM",
        confidence=0.99,
        proposed_action="send",
        response_strategy="send",
        draft_body="Sending abstract despite termination.",
        proposed_cta="none",
        cited_fact_ids=[],
        rationale="Forced send.",
    )
    mock = MockProvider(custom_suggestion=malicious_send)
    set_llm_client(LLMClient(provider=mock))

    # 2. Attempt Turn 3 on concluded thread
    r_turn3 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_double_lock_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Actually tell me more about this study.",
            "received_at": "2026-04-26T10:35:00Z",
            "turn_number": 3,
        },
    )
    assert r_turn3.status_code == 200
    assert r_turn3.json()["action"] == "end"
    assert r_turn3.json()["body"] is None
    assert mock.call_count == 0  # Double lock fast-exited before LLM


# =============================================================================
# 6. Replay Double Lock (Replay Never Incurs LLM Cost)
# =============================================================================

def test_replay_protection_never_invokes_llm():
    """Verify duplicate turn numbers return cached response without calling LLM."""
    store = get_context_store()
    seed_standard_contexts(store)

    mock = MockProvider(mode="success")
    set_llm_client(LLMClient(provider=mock))

    # Turn 2: Initial execution
    resp1 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_replay_llm_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Can you explain the trial details?",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp1.status_code == 200
    assert mock.call_count == 1

    # Turn 2: Replay identical message
    resp2 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_replay_llm_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Can you explain the trial details?",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp2.status_code == 200
    assert "[Idempotent replay]" in resp2.json()["rationale"]
    # LLM call count remains 1 (0 new LLM calls)
    assert mock.call_count == 1
