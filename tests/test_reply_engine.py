"""
Comprehensive Test Suite for Phase 3B: Deterministic Conversation Engine (/v1/reply).

Tests:
1. Positive affirmation (lowercase, uppercase, punctuation)
2. Action mode transitions (abstract + patient draft deliverable)
3. Direct rejection & graceful exit
4. Hard opt-out & hostile handling
5. Opt-out precedence over affirmation ("Yes, but stop messaging me")
6. Auto-reply detection (wait 14400s on turn 2)
7. Repeated auto-reply loop termination (end on turn 3+)
8. Out-of-scope curveball redirection (GST filing)
9. Factual questions with known sample sizes (trial_n = 2100)
10. Factual questions with missing sample sizes (zero hallucinations)
11. Ambiguous messages & low-friction clarifications
12. Duplicate turn replay idempotency
13. Stale turn rejection (HTTP 400)
14. Future skipped turn rejection (HTTP 400)
15. Merchant ID mismatch validation (HTTP 400)
16. Empty message validation (HTTP 400)
17. Invalid from_role validation (HTTP 400)
18. Emoji inputs ("👍", "???")
19. Multi-tenant suppression isolation & post opt-out tick blocking
20. No unperformed external action claims ("drafted", "prepared", never "published/scheduled")
21. Persistent SQLite survival across fresh ContextStore instances
22. Proactive tick creates persistent Turn 1 conversation state
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store.context_store import ContextStore, get_context_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure a fresh database before and after each test."""
    store = get_context_store()
    store.clear()
    yield
    store.clear()


def seed_standard_contexts(store: ContextStore):
    """Seed standard Category, Merchant, and Trigger contexts for testing."""
    # 1. Category Context (dentists)
    cat_payload = {
        "slug": "dentists",
        "voice": {
            "tone": "peer_clinical",
            "salutation_examples": ["Dr. Meera", "Dr. Sharma"],
            "vocab_allowed": ["caries", "fluoride varnish"],
            "vocab_taboo": ["guaranteed", "100% safe", "cure"],
        },
        "digest": [
            {
                "id": "d_fluoride_2026",
                "kind": "research",
                "title": "3-month fluoride recall cuts caries recurrence 38% better than 6-month",
                "source": "JIDA Oct 2026, p.14",
                "trial_n": 2100,
                "patient_segment": "high_risk_adults",
                "summary": "Randomized trial of 2,100 patients demonstrated 38% reduction in caries.",
            }
        ],
        "patient_content_library": [
            {
                "id": "pc_001",
                "title": "Recall Dental Care",
                "body": "3-month vs 6-month cleaning — does it matter? Research shows yes if you're prone to cavities. Call our clinic for a check-up.",
            }
        ],
    }
    store.save_context("category", "dentists", 1, cat_payload, "2026-04-26T10:00:00Z")

    # 2. Merchant Context
    merchant_payload = {
        "merchant_id": "m_001_drmeera",
        "category_slug": "dentists",
        "identity": {
            "name": "Dr. Meera's Dental Clinic",
            "city": "Delhi",
            "locality": "Lajpat Nagar",
            "owner_first_name": "Meera",
            "verified": True,
            "languages": ["en", "hi"],
        },
        "subscription": {"status": "active", "plan": "Pro", "days_remaining": 90},
        "performance": {"views": 2400, "ctr": 0.025},
        "customer_aggregate": {"high_risk_adult_count": 120},
        "signals": ["high_risk_adult_cohort"],
        "conversation_history": [],
    }
    store.save_context("merchant", "m_001_drmeera", 1, merchant_payload, "2026-04-26T10:00:00Z")

    # 3. Trigger Context
    trg_payload = {
        "id": "trg_digest_001",
        "scope": "merchant",
        "kind": "research_digest",
        "source": "external",
        "merchant_id": "m_001_drmeera",
        "urgency": 3,
        "suppression_key": "research:dentists:2026-W17",
        "expires_at": "2026-05-30T00:00:00Z",
        "payload": {
            "category": "dentists",
            "top_item_id": "d_fluoride_2026",
            "suppression_key": "research:dentists:2026-W17",
            "urgency": 3,
            "merchant_id": "m_001_drmeera",
        },
    }
    store.save_context("trigger", "trg_digest_001", 1, trg_payload, "2026-04-26T10:00:00Z")


# =============================================================================
# 1. Proactive Tick & Conversation Initialization
# =============================================================================

def test_tick_initializes_conversation_state():
    """Verify that /v1/tick creates Turn 1 conversation state in SQLite."""
    store = get_context_store()
    seed_standard_contexts(store)

    tick_resp = client.post(
        "/v1/tick",
        json={"now": "2026-04-26T10:30:00Z", "available_triggers": ["trg_digest_001"]},
    )
    assert tick_resp.status_code == 200
    data = tick_resp.json()
    assert len(data["actions"]) == 1

    conv_id = data["actions"][0]["conversation_id"]
    conv = store.get_conversation(conv_id)
    assert conv is not None
    assert conv["merchant_id"] == "m_001_drmeera"
    assert conv["current_turn"] == 1
    assert conv["current_state"] == "AWAITING_REPLY"

    turn1 = store.get_turn(conv_id, 1)
    assert turn1 is not None
    assert turn1["from_role"] == "vera"
    assert turn1["action"] == "send"


# =============================================================================
# 2. Positive Affirmation & Action Mode Transitions
# =============================================================================

def test_affirmation_switches_to_action_mode():
    """Verify 'Yes please send the abstract and draft' switches to action mode without qualifying."""
    store = get_context_store()
    seed_standard_contexts(store)

    # Initialize via tick
    tick_resp = client.post(
        "/v1/tick",
        json={"now": "2026-04-26T10:30:00Z", "available_triggers": ["trg_digest_001"]},
    )
    conv_id = tick_resp.json()["actions"][0]["conversation_id"]

    reply_resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": conv_id,
            "merchant_id": "m_001_drmeera",
            "customer_id": None,
            "from_role": "merchant",
            "message": "Yes please send the abstract. Also draft the patient WhatsApp.",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert reply_resp.status_code == 200
    data = reply_resp.json()
    assert data["action"] == "send"
    assert data["body"] is not None

    body_lower = data["body"].lower()
    # Must contain action/deliverable language
    assert any(w in body_lower for w in ["sending", "prepared", "draft", "here"])
    # Must NOT continue qualifying
    assert not any(w in body_lower for w in ["would you like me to tell you what", "do you think we should", "what if"])
    # Must NOT claim external execution was completed
    assert not any(w in body_lower for w in ["published", "sent to patients", "scheduled post"])


def test_uppercase_and_punctuation_affirmation():
    """Verify 'YES!!!' and 'ok lets do it' are correctly classified as affirmation."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp1 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_affirm_upper",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "YES!!!",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp1.status_code == 200
    assert resp1.json()["action"] == "send"

    resp2 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_affirm_phrase",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Ok lets do it. Whats next?",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["action"] == "send"


# =============================================================================
# 3. Direct Rejection & Graceful Exit
# =============================================================================

def test_direct_rejection_ends_conversation():
    """Verify 'Not interested.' and 'No thanks' terminate the conversation."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_reject_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Not interested. No thanks.",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "end"
    assert data["body"] is None


# =============================================================================
# 4. Hard Opt-Out & Hostile Handling
# =============================================================================

def test_hostile_opt_out_ends_and_suppresses():
    """Verify 'Stop messaging me. This is spam.' terminates and records suppression."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_hostile_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Stop messaging me. This is useless spam.",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "end"

    # Verify merchant is now suppressed
    assert store.is_suppressed("merchant_opt_out", "m_001_drmeera")


def test_opt_out_precedence_over_affirmation():
    """Verify 'Yes, but stop messaging me' is classified as OPT_OUT (safety priority)."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_priority_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Yes, but stop messaging me please.",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "end"
    assert store.is_suppressed("merchant_opt_out", "m_001_drmeera")


# =============================================================================
# 5. Auto-Reply Detection & Backoff
# =============================================================================

def test_auto_reply_first_occurrence_waits():
    """Verify standard WhatsApp greeting returns action: 'wait' with wait_seconds = 14400."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_auto_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Thank you for contacting Dr. Meera's Clinic! Our team will respond shortly.",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "wait"
    assert data["wait_seconds"] == 14400


def test_repeated_auto_reply_loop_terminates():
    """Verify repeated auto-reply terminates with action: 'end' on turn 3+."""
    store = get_context_store()
    seed_standard_contexts(store)

    # Turn 2: First auto-reply -> wait
    resp1 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_auto_repeat",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Thank you for contacting us! Our team will respond shortly.",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp1.json()["action"] == "wait"

    # Turn 3: Second auto-reply -> end
    resp2 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_auto_repeat",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Thank you for contacting us! Our team will respond shortly.",
            "received_at": "2026-04-26T14:45:00Z",
            "turn_number": 3,
        },
    )
    assert resp2.json()["action"] == "end"


# =============================================================================
# 6. Out-of-Scope Curveball Redirection
# =============================================================================

def test_out_of_scope_gst_curveball():
    """Verify GST filing request is politely declined and redirected to clinical topic."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_curveball_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Can you also help me with my GST filing this month?",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "send"
    assert "ca" in data["body"].lower() or "outside" in data["body"].lower()
    assert "clinical" in data["body"].lower() or "abstract" in data["body"].lower()


# =============================================================================
# 7. Factual Questions & Grounding Verification
# =============================================================================

def test_factual_question_with_known_fact():
    """Verify asking about sample size returns 2,100 from CategoryContext digest."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_fact_01",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "How many patients were in that study?",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "send"
    assert "2,100" in data["body"] or "2100" in data["body"]


def test_factual_question_with_missing_fact():
    """Verify that when trial_n is None, Vera safely states context does not specify."""
    store = get_context_store()
    seed_standard_contexts(store)

    # Overwrite category digest with missing trial_n
    cat_payload = {
        "slug": "dentists",
        "voice": {"tone": "peer_clinical"},
        "digest": [{"id": "d_no_n", "title": "New protocol", "summary": "Study on cleaning", "trial_n": None}],
    }
    store.save_context("category", "dentists", 2, cat_payload, "2026-04-26T10:00:00Z")

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_fact_missing",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "What was the sample size?",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "send"
    assert "does not specify" in data["body"].lower()


# =============================================================================
# 8. Ambiguous Messages & Emoji Handling
# =============================================================================

def test_ambiguous_message_clarifies():
    """Verify 'maybe' or 'tell me more' provides clarification without assuming YES."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_ambiguous",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "maybe",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "send"
    assert "abstract" in data["body"].lower() or "details" in data["body"].lower()


def test_emoji_and_thumbs_up_affirmation():
    """Verify thumbs-up emoji '👍' is treated as affirmation."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_emoji_thumbs",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "👍",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "send"


# =============================================================================
# 9. Turn Order & Idempotent Replay Protection
# =============================================================================

def test_duplicate_turn_returns_idempotent_response():
    """Verify sending turn 2 twice returns the identical cached response."""
    store = get_context_store()
    seed_standard_contexts(store)

    req_payload = {
        "conversation_id": "conv_idempotent_test",
        "merchant_id": "m_001_drmeera",
        "from_role": "merchant",
        "message": "Yes send it",
        "received_at": "2026-04-26T10:45:00Z",
        "turn_number": 2,
    }

    resp1 = client.post("/v1/reply", json=req_payload)
    assert resp1.status_code == 200

    resp2 = client.post("/v1/reply", json=req_payload)
    assert resp2.status_code == 200
    assert resp1.json()["action"] == resp2.json()["action"]
    assert resp1.json()["body"] == resp2.json()["body"]


def test_stale_turn_rejected_with_400():
    """Verify sending turn 1 after turn 2 is rejected with HTTP 400."""
    store = get_context_store()
    seed_standard_contexts(store)

    # Process Turn 2
    client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_stale_test",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Yes",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )

    # Send Stale Turn 1
    stale_resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_stale_test",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Stale repeat",
            "received_at": "2026-04-26T10:50:00Z",
            "turn_number": 1,
        },
    )
    assert stale_resp.status_code == 400
    assert "stale" in stale_resp.json()["detail"]


def test_future_skipped_turn_rejected_with_400():
    """Verify sending turn 5 when conversation is at turn 1 is rejected with HTTP 400."""
    store = get_context_store()
    seed_standard_contexts(store)

    # Proactive tick creates Turn 1
    tick_resp = client.post(
        "/v1/tick",
        json={"now": "2026-04-26T10:30:00Z", "available_triggers": ["trg_digest_001"]},
    )
    conv_id = tick_resp.json()["actions"][0]["conversation_id"]

    # Send skipped Turn 4
    future_resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": conv_id,
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Skipped ahead",
            "received_at": "2026-04-26T10:50:00Z",
            "turn_number": 4,
        },
    )
    assert future_resp.status_code == 400
    assert "out_of_order" in future_resp.json()["detail"]


# =============================================================================
# 10. Validation Failures
# =============================================================================

def test_merchant_id_mismatch_rejected():
    """Verify providing wrong merchant_id on existing conversation is rejected."""
    store = get_context_store()
    seed_standard_contexts(store)

    # Proactive tick creates Turn 1 for m_001_drmeera
    tick_resp = client.post(
        "/v1/tick",
        json={"now": "2026-04-26T10:30:00Z", "available_triggers": ["trg_digest_001"]},
    )
    conv_id = tick_resp.json()["actions"][0]["conversation_id"]

    mismatch_resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": conv_id,
            "merchant_id": "m_wrong_merchant",
            "from_role": "merchant",
            "message": "Yes",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert mismatch_resp.status_code == 400


def test_empty_message_rejected():
    """Verify empty string message is rejected with HTTP 400."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_empty_msg",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "   ",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 400


def test_invalid_from_role_rejected():
    """Verify role other than merchant or customer is rejected with HTTP 400."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_invalid_role",
            "merchant_id": "m_001_drmeera",
            "from_role": "admin",
            "message": "Hello",
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 400


# =============================================================================
# 11. Persistence Across SQLite Restarts
# =============================================================================

def test_conversation_state_survives_process_restart(tmp_path):
    """Verify conversation and turn history survive when a fresh ContextStore is created."""
    db_file = str(tmp_path / "test_restart.db")
    store1 = ContextStore(db_path=db_file)

    store1.save_conversation(
        conversation_id="conv_restart_01",
        merchant_id="m_001_drmeera",
        customer_id=None,
        trigger_id="trg_01",
        suppression_key="key_01",
        category_slug="dentists",
        current_state="AWAITING_REPLY",
        current_turn=1,
        auto_reply_count=0,
        last_action="send",
        last_body="Initial tick",
        last_rationale="Proactive digest",
    )
    store1.record_turn(
        conversation_id="conv_restart_01",
        turn_number=1,
        from_role="vera",
        message="Initial tick",
        intent="PROACTIVE",
        state_after="AWAITING_REPLY",
        action="send",
        body="Initial tick",
        rationale="Proactive digest",
    )

    # Create fresh independent store instance pointing to same db_file
    store2 = ContextStore(db_path=db_file)
    conv = store2.get_conversation("conv_restart_01")
    assert conv is not None
    assert conv["merchant_id"] == "m_001_drmeera"
    assert conv["current_turn"] == 1

    turn1 = store2.get_turn("conv_restart_01", 1)
    assert turn1 is not None
    assert turn1["body"] == "Initial tick"


# =============================================================================
# 12. Hostile Adversarial Attack Matrix
# =============================================================================

@pytest.mark.parametrize(
    "msg,expected_action",
    [
        ("yes", "send"),
        ("YES", "send"),
        ("yes!", "send"),
        ("yes?", "send"),  # Questioning affirmation clarifies, action send
        ("sure", "send"),
        ("sure?", "send"),
        ("okay", "send"),
        ("okay?", "send"),
        ("yes please", "send"),
        ("YES!!!", "send"),
        ("ok do it", "send"),
        ("send it", "send"),
        ("send it and stop messaging me", "end"),  # Opt-out priority over send
        ("go ahead", "send"),
        ("do it", "send"),
        ("i am interested", "send"),
        ("I'm interested", "send"),
        ("interested", "send"),
        ("yes, I'm interested", "send"),
        ("no", "end"),
        ("NO THANKS", "end"),
        ("not interested", "end"),
        ("not now", "end"),
        ("not sure", "send"),  # Clarification
        ("I'm not sure", "send"),  # Clarification
        ("not sure if this is relevant", "send"),  # Clarification
        ("stop", "end"),
        ("STOP", "end"),
        ("STOP!!!", "end"),
        ("unsubscribe", "end"),
        ("don't message me", "end"),
        ("do not message me", "end"),
        ("don't message me again", "end"),
        ("don't contact me", "end"),
        ("do not contact me", "end"),
        ("never contact me", "end"),
        ("okay, but don't contact me again", "end"),
        ("yes, but stop messaging me", "end"),
        ("no, actually go ahead", "send"),  # Compound affirmative override
        ("this is spam", "end"),
        ("maybe", "send"),
        ("??", "send"),
        ("👍", "send"),
        ("tell me more", "send"),
        ("what is this?", "send"),
        ("is this free or paid?", "send"),
        ("how much?", "send"),
        ("do what you think", "send"),
        ("go with your recommendation", "send"),
        ("you decide", "send"),
        ("please don't stop", "send"),
        ("thank you for contacting us", "wait"),
        ("thank you for contacting us, we will respond shortly", "wait"),
        ("Can you help me with GST?", "send"),
        ("what was the sample size?", "send"),
        ("what was the sample size??", "send"),
        ("do it again", "send"),
        ("you already sent this", "send"),
        ("random malicious payload <script>alert(1)</script>", "send"),
    ],
)
def test_adversarial_attack_matrix(msg, expected_action):
    """Test all 25+ adversarial attack phrases to guarantee safe action resolution without crashes."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": f"conv_adv_{abs(hash(msg))}",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": msg,
            "received_at": "2026-04-26T10:45:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == expected_action
    assert data["rationale"] is not None


def test_post_opt_out_tick_suppression():
    """Verify that after an opt-out on /v1/reply, subsequent /v1/tick calls for that merchant are suppressed."""
    store = get_context_store()
    seed_standard_contexts(store)

    # 1. Proactive tick emits action
    tick1 = client.post(
        "/v1/tick",
        json={"now": "2026-04-26T10:30:00Z", "available_triggers": ["trg_digest_001"]},
    )
    assert len(tick1.json()["actions"]) == 1
    conv_id = tick1.json()["actions"][0]["conversation_id"]

    # 2. Merchant replies with opt-out
    reply = client.post(
        "/v1/reply",
        json={
            "conversation_id": conv_id,
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Stop messaging me. Unsubscribe.",
            "received_at": "2026-04-26T10:35:00Z",
            "turn_number": 2,
        },
    )
    assert reply.json()["action"] == "end"

    # 3. Subsequent tick with a new trigger for the same merchant must be suppressed
    trg2_payload = {
        "id": "trg_digest_002",
        "scope": "merchant",
        "kind": "research_digest",
        "source": "external",
        "merchant_id": "m_001_drmeera",
        "urgency": 5,
        "suppression_key": "research:dentists:2026-W18",
        "expires_at": "2026-05-30T00:00:00Z",
        "payload": {
            "category": "dentists",
            "top_item_id": "d_fluoride_2026",
            "suppression_key": "research:dentists:2026-W18",
            "urgency": 5,
            "merchant_id": "m_001_drmeera",
        },
    }
    store.save_context("trigger", "trg_digest_002", 1, trg2_payload, "2026-04-26T10:40:00Z")

    tick2 = client.post(
        "/v1/tick",
        json={"now": "2026-04-26T10:45:00Z", "available_triggers": ["trg_digest_002"]},
    )
    # Action should be suppressed because merchant opted out
    assert len(tick2.json()["actions"]) == 0


# =============================================================================
# 13. Phase 3B.1 Specific Hardening Tests
# =============================================================================

def test_terminal_state_lockout_after_opt_out():
    """Verify Turn 3 on OPT_OUT conversation returns action: 'end' without side effects."""
    store = get_context_store()
    seed_standard_contexts(store)

    # Turn 2: Opt-Out
    r_opt = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_lockout_opt",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Stop messaging me. This is spam.",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert r_opt.json()["action"] == "end"

    # Turn 3: Attempt to send affirmation on concluded thread
    r_turn3 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_lockout_opt",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Actually send the abstract.",
            "received_at": "2026-04-26T10:35:00Z",
            "turn_number": 3,
        },
    )
    assert r_turn3.status_code == 200
    assert r_turn3.json()["action"] == "end"
    assert r_turn3.json()["body"] is None
    assert "concluded" in r_turn3.json()["rationale"].lower()


def test_terminal_state_lockout_after_rejection():
    """Verify Turn 3 on REJECT conversation returns action: 'end' without side effects."""
    store = get_context_store()
    seed_standard_contexts(store)

    # Turn 2: Reject
    r_rej = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_lockout_rej",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Not interested. No thanks.",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert r_rej.json()["action"] == "end"

    # Turn 3: Attempt follow-on
    r_turn3 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_lockout_rej",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Actually yes, go ahead.",
            "received_at": "2026-04-26T10:35:00Z",
            "turn_number": 3,
        },
    )
    assert r_turn3.status_code == 200
    assert r_turn3.json()["action"] == "end"
    assert r_turn3.json()["body"] is None


def test_negation_uncertainty_does_not_become_affirmation():
    """Verify 'I'm not sure' and 'not sure if this is relevant' do NOT trigger action mode."""
    store = get_context_store()
    seed_standard_contexts(store)

    for msg in ["I'm not sure", "not sure", "not sure if this is relevant", "I am not sure", "not ready", "never mind"]:
        resp = client.post(
            "/v1/reply",
            json={
                "conversation_id": f"conv_neg_{abs(hash(msg))}",
                "merchant_id": "m_001_drmeera",
                "from_role": "merchant",
                "message": msg,
                "received_at": "2026-04-26T10:30:00Z",
                "turn_number": 2,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "send"
        # Must be clarification, NOT immediate action delivery
        assert "sending the abstract summary now" not in data["body"].lower()


def test_contact_opt_out_variants():
    """Verify 'don't contact me again' and 'please don't contact me' are recognized as OPT_OUT."""
    store = get_context_store()
    seed_standard_contexts(store)

    for msg in [
        "don't contact me",
        "do not contact me",
        "don't contact me again",
        "please don't contact me",
        "never contact me",
        "okay, but don't contact me again",
    ]:
        resp = client.post(
            "/v1/reply",
            json={
                "conversation_id": f"conv_contact_opt_{abs(hash(msg))}",
                "merchant_id": "m_001_drmeera",
                "from_role": "merchant",
                "message": msg,
                "received_at": "2026-04-26T10:30:00Z",
                "turn_number": 2,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "end"


def test_questioning_affirmation_does_not_commit():
    """Verify 'sure?' and 'yes?' are treated as inquiries/doubt, not unconditional action commitment."""
    store = get_context_store()
    seed_standard_contexts(store)

    for msg in ["yes?", "YES?", "sure?", "okay?", "yes?!", "sure..."]:
        resp = client.post(
            "/v1/reply",
            json={
                "conversation_id": f"conv_q_affirm_{abs(hash(msg))}",
                "merchant_id": "m_001_drmeera",
                "from_role": "merchant",
                "message": msg,
                "received_at": "2026-04-26T10:30:00Z",
                "turn_number": 2,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "send"
        # Must clarify, not switch to action mode
        assert "sending the abstract summary now" not in data["body"].lower()


def test_positive_interest_and_delegation():
    """Verify positive interest ('I am interested') and delegation ('do what you think') switch to action mode."""
    store = get_context_store()
    seed_standard_contexts(store)

    for msg in [
        "i am interested",
        "I'm interested",
        "interested",
        "yes, I'm interested",
        "do what you think",
        "go with your recommendation",
        "you decide",
        "use your judgment",
        "do whatever you recommend",
        "no, actually go ahead",
    ]:
        resp = client.post(
            "/v1/reply",
            json={
                "conversation_id": f"conv_pos_del_{abs(hash(msg))}",
                "merchant_id": "m_001_drmeera",
                "from_role": "merchant",
                "message": msg,
                "received_at": "2026-04-26T10:30:00Z",
                "turn_number": 2,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "send"
        assert "sending" in data["body"].lower() or "draft" in data["body"].lower()


def test_replay_payload_mutation_rejected_with_409():
    """Verify duplicate turn with mutated message payload is rejected with HTTP 409 Conflict."""
    store = get_context_store()
    seed_standard_contexts(store)

    # Turn 2: Initial message "Yes send it"
    resp1 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_replay_mut",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Yes send it",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp1.status_code == 200

    # Turn 2: Identical message -> 200 OK idempotent cached
    resp2 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_replay_mut",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Yes send it",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["action"] == resp1.json()["action"]

    # Turn 2: Mutated message "Stop messaging" on same turn number -> 409 Conflict
    resp3 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_replay_mut",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "Stop messaging me",
            "received_at": "2026-04-26T10:35:00Z",
            "turn_number": 2,
        },
    )
    assert resp3.status_code == 409
    assert "conflict" in resp3.json()["detail"].lower()


def test_please_dont_stop_handling():
    """Verify 'please don't stop' does NOT trigger opt-out suppression."""
    store = get_context_store()
    seed_standard_contexts(store)

    resp = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_dont_stop",
            "merchant_id": "m_001_drmeera",
            "from_role": "merchant",
            "message": "please don't stop, send it",
            "received_at": "2026-04-26T10:30:00Z",
            "turn_number": 2,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "send"
    assert not store.is_suppressed("merchant_opt_out", "m_001_drmeera")


