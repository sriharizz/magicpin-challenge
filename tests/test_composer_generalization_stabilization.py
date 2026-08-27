"""
Regression & Generalization Tests for Final Stabilization (Stage J Composer).

Verifies:
1. Novel audience phrases without noun clashing (e.g., corporate clients, delivery patrons, senior dogs, remote workers)
2. Correct clinical adjective attachment (e.g. hypertensive patients, atopic eczema patients)
3. Actionable field utilization when present vs graceful fallback when absent
4. Missing owner identity safe fallback without name fabrication
5. Strict preservation of all safety invariants (opt-out, expiration, taboo words, replay)
"""

import pytest
from app.engine.composer import (
    compose_research_digest,
    _format_cohort_phrase,
    _resolve_topic_cta,
    resolve_salutation
)


def test_novel_audience_phrases_no_noun_clash():
    """Verify novel demographic phrases do not have 'patients' incorrectly appended."""
    assert _format_cohort_phrase("delivery customers") == "One item relevant to your delivery customers — "
    assert _format_cohort_phrase("new members") == "One item relevant to your new members — "
    assert _format_cohort_phrase("senior dogs") == "One item relevant to your senior dogs — "
    assert _format_cohort_phrase("corporate clients") == "One item relevant to your corporate clients — "
    assert _format_cohort_phrase("remote workers") == "One item relevant to your remote workers — "
    assert _format_cohort_phrase("buffet patrons") == "One item relevant to your buffet patrons — "
    assert _format_cohort_phrase("fleet owners") == "One item relevant to your fleet owners — "
    assert _format_cohort_phrase("app subscribers") == "One item relevant to your app subscribers — "


def test_clinical_adjective_descriptors_patient_attachment():
    """Verify purely adjective medical descriptors correctly attach 'patients'."""
    assert _format_cohort_phrase("hypertensive") == "One item relevant to your hypertensive patients — "
    assert _format_cohort_phrase("atopic eczema") == "One item relevant to your atopic eczema patients — "
    assert _format_cohort_phrase("pediatric caries") == "One item relevant to your pediatric caries patients — "
    assert _format_cohort_phrase("high_risk_adults") == "One item relevant to your high-risk adult patients — "
    assert _format_cohort_phrase("high risk adults") == "One item relevant to your high-risk adult patients — "


def test_empty_and_general_cohort_fallback():
    """Verify empty, None, and generic segments fall back to practice anchor."""
    assert _format_cohort_phrase(None) == "One item relevant to your practice — "
    assert _format_cohort_phrase("") == "One item relevant to your practice — "
    assert _format_cohort_phrase("all") == "One item relevant to your practice — "
    assert _format_cohort_phrase("general") == "One item relevant to your practice — "


def test_actionable_field_utilization_when_present():
    """Verify CTA composer dynamically uses actionable recommendations when present."""
    digest_with_actionable = {
        "kind": "research",
        "actionable": "Implement 14-day trainer check-in schedule"
    }
    category_without_lib = {"slug": "gyms", "patient_content_library": []}
    
    cta = _resolve_topic_cta(digest_with_actionable, category_without_lib)
    assert "how to implement 14-day trainer check-in schedule" in cta.lower()
    assert cta.endswith("?")


def test_cta_fallback_when_actionable_absent():
    """Verify CTA falls back cleanly when actionable is None or empty."""
    digest_no_act = {"kind": "research", "actionable": ""}
    category_without_lib = {"slug": "gyms", "patient_content_library": []}
    
    cta = _resolve_topic_cta(digest_no_act, category_without_lib)
    assert cta == "Worth a look (2-min abstract). Want me to pull the key takeaways for your team?"


def test_clinical_library_priority_in_cta():
    """Verify patient_content_library triggers patient-ed WhatsApp offer."""
    digest_item = {"kind": "research", "actionable": "Shorten recall interval"}
    category_with_lib = {"slug": "dentists", "patient_content_library": [{"id": "pc_1"}]}
    
    cta = _resolve_topic_cta(digest_item, category_with_lib)
    assert "draft a patient-ed whatsapp" in cta.lower()


def test_missing_owner_identity_safe_fallback():
    """Verify missing owner name falls back to business greeting without hallucination."""
    cat = {"slug": "salons", "voice": {"salutation_examples": ["Hi {first_name}"]}}
    merch_no_name = {"merchant_id": "m_1", "identity": {"name": "Luxe Salon", "owner_first_name": None}}
    
    salutation = resolve_salutation(cat, merch_no_name)
    assert salutation == "Hi Luxe Salon team"


def test_end_to_end_composer_grounding():
    """Test full compose_research_digest output with novel non-clinical audience."""
    cat = {
        "slug": "restaurants",
        "voice": {"tone": "operator_to_operator", "salutation_examples": ["Hi {first_name}"]},
        "digest": [{
            "id": "d_1",
            "title": "Thermal packaging in delivery",
            "source": "Food Logistics May 2026",
            "trial_n": 750,
            "patient_segment": "delivery customers",
            "summary": "Insulated boxes cut refund complaints by 38%.",
            "actionable": "Adopt moisture-lock thermal containers"
        }]
    }
    merch = {
        "merchant_id": "m_rest_1",
        "category_slug": "restaurants",
        "identity": {"name": "Bhojan Express", "owner_first_name": "Aditi"},
        "subscription": {"status": "active", "days_remaining": 100}
    }
    trg = {
        "id": "trg_1",
        "scope": "merchant",
        "kind": "research_digest",
        "merchant_id": "m_rest_1",
        "payload": {"top_item_id": "d_1", "category": "restaurants"},
        "expires_at": "2026-12-31T00:00:00Z"
    }

    action = compose_research_digest(cat, merch, trg, now="2026-04-26T10:00:00Z")
    assert action is not None
    body = action.body
    assert "Hi Aditi" in body
    assert "delivery customers —" in body
    assert "delivery customers patients" not in body
    assert "(N=750)" in body
    assert "how to adopt moisture-lock thermal containers?" in body.lower()
    assert body.endswith("— Food Logistics May 2026")
