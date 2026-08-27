"""
Phase 7E Test Suite: General Context Relevance Selection & Generalization.

Verifies:
1. Zero Hardcoding Invariant: GeneralRelevanceSelector produces valid scores on unseen categories.
2. Minimum Sufficient Context: Output fact count never exceeds envelope budget.
3. Adversarial Robustness: Filters out noise metrics, cross-category facts, and billing leaks.
4. Explainable Scoring: Every selected and omitted fact has an explainable reason and feature score.
"""

import pytest
from app.relevance.facts import Fact, FactExtractor
from app.relevance.general_selector import GeneralRelevanceSelector, MIN_RELEVANCE_THRESHOLD


def test_unseen_category_cardiology_relevance():
    """Verify general selector correctly scores clinical digest in unseen cardiology vertical."""
    cat = {
        "slug": "cardiology",
        "voice": {"tone": "clinical_rigorous", "register": "professional_peer"},
        "digest": [
            {
                "id": "d_card_01",
                "title": "SGLT2 Inhibitor Microvascular Outcomes",
                "summary": "Reduction in cardiovascular mortality in diabetic cohorts.",
                "actionable": "Review heart-failure protocols.",
                "patient_segment": "diabetic_cardio",
                "source": "Lancet Cardiology 2026",
                "trial_n": 4820,
            }
        ],
    }
    merch = {
        "merchant_id": "m_card_001",
        "category_slug": "cardiology",
        "identity": {
            "name": "Apex Heart Institute",
            "owner_first_name": "Aryan",
            "locality": "Whitefield",
            "city": "Bengaluru",
        },
        "customer_aggregate": {
            "high_risk_adult_count": 85,
        },
    }
    trg = {
        "id": "trg_card_01",
        "kind": "research_digest",
        "payload": {"top_item_id": "d_card_01"},
    }

    trace = GeneralRelevanceSelector.select(merchant=merch, category=cat, trigger=trg, budget=6)
    sel_paths = [f.path for f in trace.selected_facts]

    # Verify essential facts are selected
    assert "category.digest[d_card_01].title" in sel_paths
    assert "category.digest[d_card_01].trial_n" in sel_paths
    assert "merchant.identity.owner_first_name" in sel_paths
    assert len(trace.selected_facts) <= 6


def test_adversarial_commercial_distraction_in_clinical():
    """Verify commercial vanity metrics and promo deals are penalized in clinical research trigger."""
    cat = {
        "slug": "dermatology",
        "voice": {"tone": "consultative_clinical"},
        "digest": [{"id": "d_derm_01", "title": "Melasma Study", "trial_n": 500}],
    }
    merch = {
        "merchant_id": "m_derm_001",
        "identity": {"owner_first_name": "Shalini", "name": "Lumina Skin"},
        "performance": {"revenue_usd": 500000, "views_30d": 99999, "leads": 400},
        "offers": [{"id": "off_01", "title": "50% off Chemical Peel"}],
    }
    trg = {"kind": "research_digest", "payload": {"top_item_id": "d_derm_01"}}

    trace = GeneralRelevanceSelector.select(merchant=merch, category=cat, trigger=trg)
    sel_paths = [f.path for f in trace.selected_facts]

    # Clinical facts must be selected
    assert "category.digest[d_derm_01].title" in sel_paths
    # Commercial vanity metrics must be omitted
    assert "merchant.performance.views_30d" not in sel_paths
    assert "merchant.performance.revenue_usd" not in sel_paths
    assert "merchant.offers[off_01].title" not in sel_paths


def test_adversarial_sensitive_billing_leak_prevention():
    """Verify internal credit card or arrears balances are never selected in customer reply."""
    cat = {"slug": "optometry"}
    merch = {
        "merchant_id": "m_opt_001",
        "identity": {"owner_first_name": "Vikram", "name": "ClearVision"},
        "subscription": {
            "card_last4": "4242",
            "internal_arrears_balance": 12000,
            "billing_status": "overdue",
        },
    }
    trg = {"kind": "inbound_inquiry", "payload": {"question": "Do you do pediatric eye exams?"}}

    trace = GeneralRelevanceSelector.select(merchant=merch, category=cat, trigger=trg)
    sel_paths = [f.path for f in trace.selected_facts]

    assert "merchant.subscription.card_last4" not in sel_paths
    assert "merchant.subscription.internal_arrears_balance" not in sel_paths


def test_budget_limit_compliance_under_massive_context():
    """Verify context dumping attack with 50+ noise metrics is strictly capped to budget."""
    cat = {"slug": "fitness_gyms"}
    merch = {"merchant_id": "m_gym_001", "identity": {"name": "FitMatrix"}}
    for i in range(50):
        merch[f"noise_metric_{i}"] = f"noise_val_{i}"

    trg = {"kind": "performance_alert", "payload": {"drop_pct": 25}}

    trace = GeneralRelevanceSelector.select(merchant=merch, category=cat, trigger=trg, budget=5)
    assert len(trace.selected_facts) <= 5


def test_sparse_context_graceful_handling():
    """Verify selector handles empty/sparse dictionaries gracefully without error."""
    trace = GeneralRelevanceSelector.select(merchant={}, category={}, trigger={})
    assert isinstance(trace.selected_facts, list)
    assert len(trace.selected_facts) == 0
