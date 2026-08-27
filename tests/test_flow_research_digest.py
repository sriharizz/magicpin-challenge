"""
Hardened adversarial tests for the deterministic research_digest flow.
Zero test-fitting, 100% generalizable verification.
"""

from fastapi.testclient import TestClient
from app.store.context_store import ContextStore


def _seed_base_dentist_category(client: TestClient):
    """Seed base category context for dentists."""
    cat_payload = {
        "slug": "dentists",
        "display_name": "Dentists",
        "voice": {
            "tone": "peer_clinical",
            "register": "respectful_collegial",
            "code_mix": "hindi_english_natural",
            "vocab_allowed": ["fluoride varnish", "scaling", "caries"],
            "vocab_taboo": ["guaranteed", "100% safe", "miracle", "best in city", "FDA-approved (use only when actually applicable)"],
            "salutation_examples": ["Dr. {first_name}", "Doc"],
        },
        "digest": [
            {
                "id": "d_2026W17_jida_fluoride",
                "kind": "research",
                "title": "3-month fluoride varnish recall outperforms 6-month for high-risk adult caries",
                "source": "JIDA Oct 2026, p.14",
                "trial_n": 2100,
                "patient_segment": "high_risk_adults",
                "summary": "Multi-center Indian trial shows 38% lower caries recurrence with 3-month vs 6-month recall in adults with active decay history. No effect in low-risk patients.",
                "actionable": "Reassess recall interval for adults flagged high-risk in your charting",
            }
        ],
        "patient_content_library": [{"id": "pc_1", "title": "Oral Health", "body": "..."}],
    }
    client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_payload, "delivered_at": "2026-04-26T10:00:00Z"})


def test_canonical_grounding_without_hardcoded_overrides(client: TestClient):
    """Verify Dr. Meera research digest composition is strictly grounded in raw context fields."""
    _seed_base_dentist_category(client)

    merchant_payload = {
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "category_slug": "dentists",
        "identity": {
            "name": "Dr. Meera's Dental Clinic",
            "city": "Delhi",
            "locality": "Lajpat Nagar",
            "verified": True,
            "languages": ["en", "hi"],
            "owner_first_name": "Meera",
        },
        "subscription": {"status": "active", "plan": "Pro", "days_remaining": 82},
        "performance": {"views": 2410, "calls": 18, "ctr": 0.021},
        "customer_aggregate": {"total_unique_ytd": 540, "high_risk_adult_count": 124},
        "signals": ["high_risk_adult_cohort", "ctr_below_peer_median"],
        "conversation_history": [],
    }

    trigger_payload = {
        "id": "trg_001_research_digest_dentists",
        "scope": "merchant",
        "kind": "research_digest",
        "source": "external",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "customer_id": None,
        "payload": {"category": "dentists", "top_item_id": "d_2026W17_jida_fluoride"},
        "urgency": 2,
        "suppression_key": "research:dentists:2026-W17",
        "expires_at": "2026-05-03T00:00:00Z",
    }

    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_001_drmeera_dentist_delhi", "version": 1, "payload": merchant_payload, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_001_research_digest_dentists", "version": 1, "payload": trigger_payload, "delivered_at": "2026-04-26T10:00:00Z"})

    tick_res = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": ["trg_001_research_digest_dentists"]})
    assert tick_res.status_code == 200
    actions = tick_res.json().get("actions", [])
    assert len(actions) == 1

    action = actions[0]
    assert action["merchant_id"] == "m_001_drmeera_dentist_delhi"
    assert action["customer_id"] is None
    assert action["send_as"] == "vera"
    assert action["trigger_id"] == "trg_001_research_digest_dentists"
    assert action["cta"] == "open_ended"
    assert action["suppression_key"] == "research:dentists:2026-W17"

    body = action["body"]
    assert "Dr. Meera" in body
    assert "JIDA's Oct issue landed" in body
    assert "2,100" in body
    assert "38%" in body
    assert "high-risk adult patients" in body
    assert "— JIDA Oct 2026, p.14" in body
    assert "Worth a look" in body


def test_multi_merchant_suppression_isolation(client: TestClient):
    """
    Verify that suppression is merchant-scoped.
    Merchant A receiving suppression_key X does NOT suppress Merchant B from receiving suppression_key X.
    """
    _seed_base_dentist_category(client)

    # Merchant A
    m_a = {"merchant_id": "m_dentist_a", "category_slug": "dentists", "identity": {"name": "Clinic A", "owner_first_name": "Asha"}, "subscription": {"status": "active"}}
    # Merchant B
    m_b = {"merchant_id": "m_dentist_b", "category_slug": "dentists", "identity": {"name": "Clinic B", "owner_first_name": "Bharat"}, "subscription": {"status": "active"}}

    # Shared external trigger suppression key
    trg_a = {"id": "trg_shared_a", "scope": "merchant", "kind": "research_digest", "merchant_id": "m_dentist_a", "payload": {"category": "dentists", "top_item_id": "d_2026W17_jida_fluoride"}, "suppression_key": "research:dentists:2026-W17", "expires_at": "2026-05-30T00:00:00Z"}
    trg_b = {"id": "trg_shared_b", "scope": "merchant", "kind": "research_digest", "merchant_id": "m_dentist_b", "payload": {"category": "dentists", "top_item_id": "d_2026W17_jida_fluoride"}, "suppression_key": "research:dentists:2026-W17", "expires_at": "2026-05-30T00:00:00Z"}

    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_dentist_a", "version": 1, "payload": m_a, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_dentist_b", "version": 1, "payload": m_b, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_shared_a", "version": 1, "payload": trg_a, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_shared_b", "version": 1, "payload": trg_b, "delivered_at": "2026-04-26T10:00:00Z"})

    # Tick 1: Both A and B must receive the action!
    res1 = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": ["trg_shared_a", "trg_shared_b"]})
    actions1 = res1.json().get("actions", [])
    assert len(actions1) == 2
    merchant_ids_sent = {a["merchant_id"] for a in actions1}
    assert "m_dentist_a" in merchant_ids_sent
    assert "m_dentist_b" in merchant_ids_sent

    # Tick 2: Both A and B are now suppressed
    res2 = client.post("/v1/tick", json={"now": "2026-04-26T10:40:00Z", "available_triggers": ["trg_shared_a", "trg_shared_b"]})
    assert len(res2.json().get("actions", [])) == 0


def test_unseen_research_digest_scenario(client: TestClient):
    """Verify completely unseen merchant, unseen journal, unseen trial numbers, and unseen patient cohort."""
    unseen_category = {
        "slug": "dermatology",
        "voice": {
            "tone": "peer_clinical",
            "salutation_examples": ["Dr. {first_name}", "Doctor"],
            "vocab_taboo": ["miracle", "100% cure"],
        },
        "digest": [
            {
                "id": "d_unseen_derma_2026",
                "kind": "research",
                "title": "Topical barrier repair in adult atopic eczema",
                "source": "Journal of Clinical Dermatology Nov 2026, p.88",
                "trial_n": 3400,
                "patient_segment": "atopic_eczema_adults",
                "summary": "Randomized multi-center trial demonstrated 52% reduction in flare frequency over 12 weeks with lipid-dominant ceramide formulation.",
                "actionable": "Consider barrier therapy protocol for severe flare cases",
            }
        ],
        "patient_content_library": [{"id": "pc_derma", "title": "Skin Barrier"}],
    }
    client.post("/v1/context", json={"scope": "category", "context_id": "dermatology", "version": 1, "payload": unseen_category, "delivered_at": "2026-04-26T10:00:00Z"})

    unseen_merchant = {
        "merchant_id": "m_unseen_drneha_mumbai",
        "category_slug": "dermatology",
        "identity": {"name": "DermaCare Clinic", "owner_first_name": "Neha", "city": "Mumbai"},
        "subscription": {"status": "active"},
        "signals": ["atopic_eczema_adults_cohort"],
    }
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_unseen_drneha_mumbai", "version": 1, "payload": unseen_merchant, "delivered_at": "2026-04-26T10:00:00Z"})

    unseen_trigger = {
        "id": "trg_unseen_derma_01",
        "scope": "merchant",
        "kind": "research_digest",
        "merchant_id": "m_unseen_drneha_mumbai",
        "payload": {"category": "dermatology", "top_item_id": "d_unseen_derma_2026"},
        "suppression_key": "research:dermatology:2026-W45",
        "expires_at": "2026-12-01T00:00:00Z",
    }
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_unseen_derma_01", "version": 1, "payload": unseen_trigger, "delivered_at": "2026-04-26T10:00:00Z"})

    res = client.post("/v1/tick", json={"now": "2026-11-10T10:00:00Z", "available_triggers": ["trg_unseen_derma_01"]})
    assert res.status_code == 200
    actions = res.json().get("actions", [])
    assert len(actions) == 1

    action = actions[0]
    body = action["body"]
    assert "Dr. Neha" in body
    assert "Journal of Clinical Dermatology's Nov issue landed" in body
    assert "atopic eczema adults" in body
    assert "52% reduction in flare frequency" in body
    assert "3,400" in body
    assert "— Journal of Clinical Dermatology Nov 2026, p.88" in body
    assert "trial showed trial showed" not in body


def test_fact_synthesis_variations(client: TestClient):
    """Verify robust fact synthesis for all combinations of trial_n, summary, and title."""
    from app.engine.composer import _synthesize_finding

    # 1. trial_n present + summary without N -> weaves N=(trial_n)
    s1 = _synthesize_finding("Multi-center trial shows 24% reduction in plaque accumulation", "Plaque Study", 850)
    assert s1 == "Multi-center trial shows 24% reduction in plaque accumulation (N=850)."
    assert "trial showed trial shows" not in s1

    # 2. trial_n present + summary already contains 850 -> does not duplicate
    s2 = _synthesize_finding("An 850-patient multi-center trial shows 24% reduction", "Plaque Study", 850)
    assert s2 == "An 850-patient multi-center trial shows 24% reduction."
    assert "(N=850)" not in s2

    # 3. trial_n is None + summary present -> uses summary cleanly
    s3 = _synthesize_finding("Standard scaling reduces gum inflammation markers", "Scaling", None)
    assert s3 == "Standard scaling reduces gum inflammation markers."

    # 4. summary is empty + title present -> uses title cleanly
    s4 = _synthesize_finding("", "Digital RVG sensor evaluation in Indian clinics", None)
    assert s4 == "Digital RVG sensor evaluation in Indian clinics."

    # 5. summary and title both empty -> returns None (never fabricate claim)
    s5 = _synthesize_finding("", "", 2100)
    assert s5 is None


def test_taboo_word_boundary_isolation(client: TestClient):
    """Verify that taboo checking respects word boundaries and does not mutate legitimate words."""
    from app.engine.composer import _validate_taboo_words, _clean_taboo_terms

    taboos = ["cure", "guaranteed", "100% safe", "miracle", "FDA-approved (use only when actually applicable)"]
    cleaned_taboos = _clean_taboo_terms(taboos)
    assert "FDA-approved" in cleaned_taboos
    assert "cure" in cleaned_taboos

    # Words containing 'cure' as substring must NOT be mutilated
    sentence = "Secure data protocols and accurate diagnosis ensure non-guaranteed results."
    res = _validate_taboo_words(sentence, cleaned_taboos)
    assert "Secure" in res
    assert "accurate" in res
    assert "cure" not in res.lower().split()  # Standalone 'cure' absent, but 'Secure' intact


def test_generic_journal_lead_hooks(client: TestClient):
    """Verify lead hook parsing for various publication formats without whitelists."""
    from app.engine.composer import _extract_lead_hook

    assert "JADA's Nov issue landed" in _extract_lead_hook("JADA Nov 2026, p.5")
    assert "The Lancet's Oct issue landed" in _extract_lead_hook("The Lancet Oct 2026, p.20")
    assert "BMJ's Sep issue landed" in _extract_lead_hook("BMJ Sep 2026")
    assert "Dental Council of India circular 2026-11-04 released" in _extract_lead_hook("Dental Council of India circular 2026-11-04")
    assert "IDA Delhi calendar" in _extract_lead_hook("IDA Delhi calendar 2026")
    assert "Hair Brand News India" in _extract_lead_hook("Hair Brand News India, Apr 2026")



def test_category_driven_salutations(client: TestClient):
    """Verify salutation resolution is driven by voice.salutation_examples and avoids 'Dr. None'."""
    from app.engine.salutation import resolve_salutation

    # 1. Doctor vertical with owner name
    cat_dentist = {"voice": {"salutation_examples": ["Dr. {first_name}", "Doc"]}}
    assert resolve_salutation(cat_dentist, {"identity": {"owner_first_name": "Asha"}}) == "Dr. Asha"
    assert resolve_salutation(cat_dentist, {"identity": {"owner_first_name": "Dr. Asha"}}) == "Dr. Asha"

    # 2. Doctor vertical with missing owner name
    assert resolve_salutation(cat_dentist, {"identity": {"owner_first_name": None, "name": "Asha Clinic"}}) == "Doc"
    assert resolve_salutation(cat_dentist, {"identity": {"owner_first_name": "None"}}) == "Doc"

    # 3. Salon / General vertical with owner name
    cat_salon = {"voice": {"salutation_examples": ["Hi {first_name}", "{salon_name} team"]}}
    assert resolve_salutation(cat_salon, {"identity": {"owner_first_name": "Lakshmi"}}) == "Hi Lakshmi"

    # 4. Salon with missing owner name
    assert resolve_salutation(cat_salon, {"identity": {"owner_first_name": None, "name": "Studio11"}}) == "Hi Studio11 team"

    # 5. Synthetic category with custom template pattern
    cat_synthetic = {"voice": {"salutation_examples": ["{first_name} ji", "Namaste"]}}
    assert resolve_salutation(cat_synthetic, {"identity": {"owner_first_name": "Ramesh"}}) == "Ramesh ji"
    assert resolve_salutation(cat_synthetic, {"identity": {"owner_first_name": None, "name": "Shop"}}) == "Hi Shop team"


def test_topic_aware_cta_across_digest_kinds(client: TestClient):
    """Verify CTA adapts appropriately across clinical, compliance, tech, and cde digest kinds."""
    from app.engine.composer import _resolve_topic_cta

    cat = {"slug": "dentists", "patient_content_library": [{"id": "pc1"}]}

    # Compliance
    cta_comp = _resolve_topic_cta({"kind": "compliance"}, cat)
    assert "compliance checklist" in cta_comp

    # Tech / Equipment
    cta_tech = _resolve_topic_cta({"kind": "tech"}, cat)
    assert "workflow and comparison" in cta_tech

    # CDE / Webinar
    cta_cde = _resolve_topic_cta({"kind": "cde"}, cat)
    assert "session details and credits" in cta_cde

    # Trend
    cta_trend = _resolve_topic_cta({"kind": "trend"}, cat)
    assert "local demand" in cta_trend

    # Research with patient content library
    cta_res = _resolve_topic_cta({"kind": "research"}, cat)
    assert "patient-ed WhatsApp" in cta_res


def test_tick_action_cap_20(client: TestClient):
    """Verify that /v1/tick strictly enforces the 20-action cap and prioritizes by highest urgency first."""
    _seed_base_dentist_category(client)

    # Seed 25 merchants and 25 triggers with varying urgencies
    trg_ids = []
    for i in range(1, 26):
        mid = f"m_cap_{i:03d}"
        tid = f"trg_cap_{i:03d}"
        trg_ids.append(tid)
        urgency = 5 if i > 20 else (3 if i > 10 else 1)

        m_payload = {"merchant_id": mid, "category_slug": "dentists", "identity": {"name": f"Clinic {i}", "owner_first_name": f"Doctor{i}"}, "subscription": {"status": "active"}}
        t_payload = {"id": tid, "scope": "merchant", "kind": "research_digest", "merchant_id": mid, "payload": {"category": "dentists", "top_item_id": "d_2026W17_jida_fluoride"}, "urgency": urgency, "suppression_key": f"suppress:{mid}", "expires_at": "2026-12-30T00:00:00Z"}

        client.post("/v1/context", json={"scope": "merchant", "context_id": mid, "version": 1, "payload": m_payload, "delivered_at": "2026-04-26T10:00:00Z"})
        client.post("/v1/context", json={"scope": "trigger", "context_id": tid, "version": 1, "payload": t_payload, "delivered_at": "2026-04-26T10:00:00Z"})

    res = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": trg_ids})
    assert res.status_code == 200
    actions = res.json().get("actions", [])

    # Strict assertion: never more than 20
    assert len(actions) == 20

    # Highest urgency triggers (urgency=5, i in 21..25) must be present in output
    high_urgency_trigger_ids = {f"trg_cap_{i:03d}" for i in range(21, 26)}
    emitted_trigger_ids = {a["trigger_id"] for a in actions}
    assert high_urgency_trigger_ids.issubset(emitted_trigger_ids)


def test_expired_trigger_suppression(client: TestClient):
    """Verify that an expired trigger is gracefully suppressed."""
    _seed_base_dentist_category(client)

    m = {"merchant_id": "m_exp", "category_slug": "dentists", "identity": {"name": "Exp Clinic", "owner_first_name": "Asha"}, "subscription": {"status": "active"}}
    t = {"id": "trg_exp", "scope": "merchant", "kind": "research_digest", "merchant_id": "m_exp", "payload": {"category": "dentists", "top_item_id": "d_2026W17_jida_fluoride"}, "suppression_key": "suppress:exp", "expires_at": "2026-05-01T00:00:00Z"}

    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_exp", "version": 1, "payload": m, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_exp", "version": 1, "payload": t, "delivered_at": "2026-04-26T10:00:00Z"})

    # Now is later than expires_at
    res = client.post("/v1/tick", json={"now": "2026-05-02T00:00:00Z", "available_triggers": ["trg_exp"]})
    assert len(res.json().get("actions", [])) == 0


def test_category_mismatch_suppression(client: TestClient):
    """Verify trigger with category mismatch to merchant is suppressed."""
    _seed_base_dentist_category(client)

    m = {"merchant_id": "m_mismatch", "category_slug": "dentists", "identity": {"name": "Dentist Clinic", "owner_first_name": "Asha"}, "subscription": {"status": "active"}}
    t = {"id": "trg_mismatch", "scope": "merchant", "kind": "research_digest", "merchant_id": "m_mismatch", "payload": {"category": "salons", "top_item_id": "d_2026W17_jida_fluoride"}, "suppression_key": "suppress:mismatch", "expires_at": "2026-12-30T00:00:00Z"}

    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_mismatch", "version": 1, "payload": m, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_mismatch", "version": 1, "payload": t, "delivered_at": "2026-04-26T10:00:00Z"})

    res = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": ["trg_mismatch"]})
    assert len(res.json().get("actions", [])) == 0


def test_opted_out_merchant_suppression(client: TestClient):
    """Verify that merchant with opt-out conversation history is suppressed."""
    _seed_base_dentist_category(client)

    m = {
        "merchant_id": "m_opted_out",
        "category_slug": "dentists",
        "identity": {"name": "Opted Out Clinic", "owner_first_name": "Rajan"},
        "subscription": {"status": "active"},
        "conversation_history": [
            {"from": "merchant", "body": "Please stop messaging me with updates", "engagement": "unsubscribed-from-topic"}
        ],
    }
    t = {"id": "trg_opted_out", "scope": "merchant", "kind": "research_digest", "merchant_id": "m_opted_out", "payload": {"category": "dentists", "top_item_id": "d_2026W17_jida_fluoride"}, "suppression_key": "suppress:opted_out", "expires_at": "2026-12-30T00:00:00Z"}

    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_opted_out", "version": 1, "payload": m, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_opted_out", "version": 1, "payload": t, "delivered_at": "2026-04-26T10:00:00Z"})

    res = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": ["trg_opted_out"]})
    assert len(res.json().get("actions", [])) == 0

