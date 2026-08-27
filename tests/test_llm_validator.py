"""
Unit & Adversarial Tests for Vera's LLM Validator and Context Envelope Builders (Phase 5A).
"""

import pytest
from app.llm.schemas import (
    LLMContextEnvelope,
    MerchantEnvelope,
    CategoryEnvelope,
    CategoryVoiceEnvelope,
    DigestItemEnvelope,
    SupportedFact,
    LLMDecisionSuggestion,
)
from app.llm.validator import LLMOutputValidator
from app.llm.prompts import build_context_envelope, format_user_prompt, SYSTEM_PROMPT
from app.store.context_store import ContextStore, get_context_store


@pytest.fixture
def sample_envelope() -> LLMContextEnvelope:
    return LLMContextEnvelope(
        merchant=MerchantEnvelope(
            merchant_id="m_001_drmeera",
            name="Dr. Meera's Clinic",
            category_slug="dentists",
            tone_preference="peer_clinical",
        ),
        category=CategoryEnvelope(
            slug="dentists",
            voice=CategoryVoiceEnvelope(
                tone="peer_clinical",
                taboo_words=["guaranteed", "miracle", "100%"],
            ),
        ),
        active_digest_item=DigestItemEnvelope(
            item_id="d_fluoride_2026",
            title="High-viscosity GIC trial",
            source="JIDA Oct 2026",
            summary="38% caries reduction in root caries.",
            trial_n=2100,
        ),
        supported_facts=[
            SupportedFact(fact_id="F1", key="trial_n", value="2,100", description="Trial sample size"),
            SupportedFact(fact_id="F2", key="caries_reduction", value="38%", description="Caries reduction rate"),
        ],
    )


def test_valid_affirmation_suggestion_passes(sample_envelope):
    """Verify clean action-mode suggestion passes validator."""
    suggestion = LLMDecisionSuggestion(
        suggested_intent="INTENT_AFFIRM",
        confidence=0.98,
        proposed_action="send",
        response_strategy="deliver_abstract_and_draft",
        draft_body="Sending the abstract summary now. I have also prepared a patient draft: Fluoride release from modern GIC reduces root caries by 38% (n=2,100). Next step: want me to prepare the follow-up recall template?",
        proposed_cta="binary_yes_no",
        cited_fact_ids=["F1", "F2"],
        rationale="Merchant confirmed delivery. Delivered draft with citations.",
    )

    res = LLMOutputValidator.validate(suggestion, sample_envelope, current_state="AWAITING_REPLY")
    assert res.is_valid is True
    assert res.sanitized_action == "send"
    assert res.fallback_required is False
    assert len(res.error_reasons) == 0


def test_qualifying_words_in_action_mode_fails(sample_envelope):
    """Verify qualifying phrases like 'would you' fail validation during action mode."""
    suggestion = LLMDecisionSuggestion(
        suggested_intent="INTENT_AFFIRM",
        confidence=0.95,
        proposed_action="send",
        response_strategy="deliver",
        draft_body="Sending the abstract now. Would you like me to tell you more about how this works?",
        proposed_cta="binary_yes_no",
        cited_fact_ids=["F1"],
        rationale="Delivered abstract.",
    )

    res = LLMOutputValidator.validate(suggestion, sample_envelope, current_state="AWAITING_REPLY")
    assert res.is_valid is False
    assert res.fallback_required is True
    assert any("qualifying" in err.lower() for err in res.error_reasons)


def test_forbidden_external_action_claim_fails(sample_envelope):
    """Verify claiming unperformed external actions ('published', 'sent to patients') fails validation."""
    suggestion = LLMDecisionSuggestion(
        suggested_intent="INTENT_AFFIRM",
        confidence=0.99,
        proposed_action="send",
        response_strategy="deliver",
        draft_body="I have published this post and sent to patients on your WhatsApp broadcast list.",
        proposed_cta="binary_yes_no",
        cited_fact_ids=[],
        rationale="Published broadcast.",
    )

    res = LLMOutputValidator.validate(suggestion, sample_envelope, current_state="AWAITING_REPLY")
    assert res.is_valid is False
    assert res.fallback_required is True
    assert any("external-action" in err.lower() for err in res.error_reasons)


def test_terminal_state_lockout_enforced(sample_envelope):
    """Verify LLM cannot suggest 'send' on a terminated conversation thread."""
    suggestion = LLMDecisionSuggestion(
        suggested_intent="INTENT_AFFIRM",
        confidence=0.99,
        proposed_action="send",
        response_strategy="deliver",
        draft_body="Sending abstract now.",
        proposed_cta="binary_yes_no",
        cited_fact_ids=[],
        rationale="Deliver.",
    )

    res = LLMOutputValidator.validate(suggestion, sample_envelope, current_state="TERMINATED_OPT_OUT")
    assert res.is_valid is False
    assert res.sanitized_action == "end"
    assert res.fallback_required is True
    assert any("terminal" in err.lower() for err in res.error_reasons)


def test_unknown_fact_citation_fails(sample_envelope):
    """Verify citing a fact_id not present in supported_facts fails validation."""
    suggestion = LLMDecisionSuggestion(
        suggested_intent="INTENT_QUESTION",
        confidence=0.90,
        proposed_action="send",
        response_strategy="answer",
        draft_body="The trial evaluated 2,100 patients with 99% success rate.",
        proposed_cta="open_ended",
        cited_fact_ids=["F1", "F99_FABRICATED"],
        rationale="Answered question.",
    )

    res = LLMOutputValidator.validate(suggestion, sample_envelope, current_state="AWAITING_REPLY")
    assert res.is_valid is False
    assert any("unknown fact" in err.lower() for err in res.error_reasons)


def test_internal_state_leakage_fails(sample_envelope):
    """Verify leaking internal enum names in draft_body fails validation."""
    suggestion = LLMDecisionSuggestion(
        suggested_intent="INTENT_AFFIRM",
        confidence=0.90,
        proposed_action="send",
        response_strategy="deliver",
        draft_body="State updated to ACTION_MODE. Sending abstract.",
        proposed_cta="binary_yes_no",
        cited_fact_ids=[],
        rationale="Update.",
    )

    res = LLMOutputValidator.validate(suggestion, sample_envelope, current_state="AWAITING_REPLY")
    assert res.is_valid is False
    assert any("internal state token" in err.lower() for err in res.error_reasons)


def test_taboo_word_scrubbed(sample_envelope):
    """Verify category taboo words are scrubbed from draft_body."""
    suggestion = LLMDecisionSuggestion(
        suggested_intent="INTENT_QUESTION",
        confidence=0.90,
        proposed_action="send",
        response_strategy="answer",
        draft_body="This is a miracle finding with 38% reduction in root caries.",
        proposed_cta="open_ended",
        cited_fact_ids=["F2"],
        rationale="Answered with reduction rate.",
    )

    res = LLMOutputValidator.validate(suggestion, sample_envelope, current_state="AWAITING_REPLY")
    assert res.is_valid is True
    assert "miracle" not in res.sanitized_body.lower()
    assert "38%" in res.sanitized_body


def test_rejection_intent_action_mismatch_fails(sample_envelope):
    """Verify INTENT_REJECT cannot propose action 'send'."""
    suggestion = LLMDecisionSuggestion(
        suggested_intent="INTENT_REJECT",
        confidence=0.95,
        proposed_action="send",
        response_strategy="retry",
        draft_body="Are you sure you do not want this?",
        proposed_cta="open_ended",
        cited_fact_ids=[],
        rationale="Retry pitch.",
    )

    res = LLMOutputValidator.validate(suggestion, sample_envelope, current_state="AWAITING_REPLY")
    assert res.is_valid is False
    assert any("proposed_action='end'" in err for err in res.error_reasons)


def test_context_envelope_builder(tmp_path):
    """Verify build_context_envelope correctly extracts facts, merchant, and category from SQLite store."""
    db_file = str(tmp_path / "test_llm_env.db")
    store = ContextStore(db_path=db_file)

    # Seed Category
    store.save_context("category", "dentists", 1, {
        "slug": "dentists",
        "voice": {"tone": "peer_clinical", "taboo_words": ["cure", "miracle"]},
        "digest": [{
            "id": "d_100",
            "title": "Caries trial",
            "source": "JIDA Nov 2026",
            "summary": "High-viscosity GIC results",
            "trial_n": 3500,
        }],
    }, "2026-04-26T10:00:00Z")

    # Seed Merchant
    store.save_context("merchant", "m_env_01", 1, {
        "merchant_id": "m_env_01",
        "category_slug": "dentists",
        "identity": {"name": "Dr. Test Clinic"},
    }, "2026-04-26T10:00:00Z")

    env = build_context_envelope(store, "conv_env_01", "m_env_01", "dentists")
    assert env.merchant.merchant_id == "m_env_01"
    assert env.category.slug == "dentists"
    assert env.category.voice.taboo_words == ["cure", "miracle"]
    assert env.active_digest_item.trial_n == 3500
    assert any(f.value == "3,500" for f in env.supported_facts)


def test_user_prompt_formatting(sample_envelope):
    """Verify format_user_prompt outputs strict envelope JSON and turn context."""
    prompt = format_user_prompt(sample_envelope, "Can you explain this for older patients?", 2)
    assert "CONTEXT ENVELOPE:" in prompt
    assert "m_001_drmeera" in prompt
    assert "F1" in prompt
    assert "Can you explain this for older patients?" in prompt
    assert len(SYSTEM_PROMPT) > 100
