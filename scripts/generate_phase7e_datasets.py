"""
Phase 7E Dataset Generator.

Generates:
1. tests/unseen_cases.json (220 novel unseen benchmark cases across 8 novel categories and novel triggers)
2. tests/adversarial_cases.json (110 adversarial distraction cases to test relevance selection robustness)
"""

import json
import random
from pathlib import Path
from typing import Dict, Any, List


NOVEL_CATEGORIES = [
    {
        "slug": "cardiology",
        "voice": {"tone": "clinical_rigorous", "register": "professional_peer", "vocab_allowed": ["ejection fraction", "hypertension", "statin", "lipid cohort"], "vocab_taboo": ["cure all", "magic pill", "guaranteed"]},
        "digest": [
            {"id": "d_card_01", "title": "SGLT2 Inhibitor Microvascular Outcomes", "summary": "Reduction in cardiovascular mortality observed across high-risk diabetic cohorts.", "actionable": "Review heart-failure protocols for diabetic patients.", "patient_segment": "diabetic_cardio", "source": "Lancet Cardiology 2026", "trial_n": 4820},
            {"id": "d_card_02", "title": "Early Statin Titration in Post-PCI Recovery", "summary": "High-intensity statin regimens reduced 90-day recurrent ischemic events.", "actionable": "Audit post-PCI lipid panel follow-ups.", "patient_segment": "post_pci", "source": "JACC 2025", "trial_n": 3200}
        ]
    },
    {
        "slug": "dermatology",
        "voice": {"tone": "consultative_clinical", "register": "peer_medical", "vocab_allowed": ["melasma", "retinoid", "barrier repair", "transepidermal"], "vocab_taboo": ["fairness", "instant glow", "bleach"]},
        "digest": [
            {"id": "d_derm_01", "title": "Topical Cysteamine vs Hydroquinone for Melasma", "summary": "Comparable efficacy with significantly lower erythema and rebound hyperpigmentation.", "actionable": "Consider non-hydroquinone protocols for recalcitrant melasma.", "patient_segment": "hyperpigmentation", "source": "JAAD 2026", "trial_n": 640}
        ]
    },
    {
        "slug": "optometry",
        "voice": {"tone": "precise_clinical", "register": "technical_peer", "vocab_allowed": ["myopia control", "orthokeratology", "axial length", "diopters"], "vocab_taboo": ["laser guarantee", "100% cure"]},
        "digest": [
            {"id": "d_opt_01", "title": "Low-Dose Atropine combined with Defocus Lenses", "summary": "Synergistic slowdown in axial elongation among pediatric progressive myopes.", "actionable": "Evaluate dual-therapy protocols for fast-progressing pediatric myopia.", "patient_segment": "pediatric_myopia", "source": "Ophthalmology 2026", "trial_n": 1250}
        ]
    },
    {
        "slug": "veterinary",
        "voice": {"tone": "compassionate_clinical", "register": "veterinary_peer", "vocab_allowed": ["canine atopy", "monoclonal", "cytopoint", "pruritus"], "vocab_taboo": ["miracle cure"]},
        "digest": [
            {"id": "d_vet_01", "title": "Long-Term Monoclonal Antibody Safety in Canine Atopy", "summary": "Sustained pruritus reduction over 24 months without immunosuppressive adverse events.", "actionable": "Review maintenance scheduling for seasonal canine atopic dermatitis.", "patient_segment": "canine_atopy", "source": "Vet Dermatology 2025", "trial_n": 890}
        ]
    },
    {
        "slug": "fitness_gyms",
        "voice": {"tone": "energetic_coaching", "register": "fitness_expert", "vocab_allowed": ["hypertrophy", "progressive overload", "retention", "re-engagement"], "vocab_taboo": ["get shredded in 3 days", "anabolic secret"]},
        "digest": []
    },
    {
        "slug": "wellness_spa",
        "voice": {"tone": "serene_consultative", "register": "hospitality_expert", "vocab_allowed": ["aromatherapy", "lymphatic drainage", "stress reduction", "repeat booking"], "vocab_taboo": ["detox guaranteed"]},
        "digest": []
    },
    {
        "slug": "ayurveda",
        "voice": {"tone": "authentic_traditional", "register": "holistic_clinical", "vocab_allowed": ["dosha", "panchakarma", "rasayana", "standardized extract"], "vocab_taboo": ["allopathic replacement", "100% cure"]},
        "digest": [
            {"id": "d_ayu_01", "title": "Standardized Ashwagandha Extract for Chronic Stress & Cortisol", "summary": "Statistically significant reduction in serum cortisol and perceived stress scores.", "actionable": "Integrate standardized botanical assessments in wellness consultations.", "patient_segment": "stress_management", "source": "Phytomedicine 2026", "trial_n": 450}
        ]
    },
    {
        "slug": "diagnostic_labs",
        "voice": {"tone": "analytical_rigorous", "register": "laboratory_peer", "vocab_allowed": ["sensitivity", "specificity", "turnaround time", "hemolysis"], "vocab_taboo": ["instant error-free"]},
        "digest": [
            {"id": "d_lab_01", "title": "Pre-Analytical Sample Quality Protocol in High-Volume Labs", "summary": "Standardized tube transport protocols cut sample rejection rates by 42%.", "actionable": "Audit phlebotomy collection transport times.", "patient_segment": "routine_biochemistry", "source": "Clinica Chimica Acta 2026", "trial_n": 15000}
        ]
    }
]

CITIES_LOCALITIES = [
    ("Bengaluru", "Whitefield"),
    ("Bengaluru", "Indiranagar"),
    ("Hyderabad", "Banjara Hills"),
    ("Hyderabad", "Gachibowli"),
    ("Chennai", "Alwarpet"),
    ("Chennai", "Anna Nagar"),
    ("Kolkata", "Salt Lake"),
    ("Delhi", "Vasant Kunj"),
    ("Delhi", "Greater Kailash"),
    ("Pune", "Koregaon Park"),
    ("Lucknow", "Gomti Nagar"),
    ("Mumbai", "Bandra West"),
    ("Jaipur", "C-Scheme"),
    ("Ahmedabad", "Bodakdev")
]

DOCTOR_NAMES = [
    "Dr. Aryan Khan", "Dr. Shalini Mukherjee", "Dr. Vikram Sethi", "Dr. Priya Nair",
    "Dr. Ananya Roy", "Dr. Rohan Deshmukh", "Dr. Sneha Pillai", "Dr. Karthik Sundaram",
    "Dr. Meera Nambiar", "Dr. Kabir Bedi", "Dr. Neha Agarwal", "Dr. Farhan Qureshi"
]

BIZ_NAMES = [
    "Apex Heart & Vascular Care", "Lumina Skin Institute", "ClearVision Eye Clinic",
    "PawCare Animal Hospital", "FitMatrix Performance Gym", "ZenVeda Ayurvedic Centre",
    "Aura Serenity Wellness Spa", "Precision Diagnostics Laboratory"
]


def generate_unseen_cases(count: int = 220) -> List[Dict[str, Any]]:
    cases = []
    triggers = ["research_digest", "performance_alert", "renewal_reminder", "seasonal_trend", "inbound_inquiry"]
    densities = ["rich", "medium", "sparse", "missing_optional"]

    for i in range(count):
        cid = f"unseen_{i+1:04d}"
        cat_meta = random.choice(NOVEL_CATEGORIES)
        cat_slug = cat_meta["slug"]
        city, locality = random.choice(CITIES_LOCALITIES)
        doc_name = random.choice(DOCTOR_NAMES)
        biz_name = f"{random.choice(BIZ_NAMES)} {locality}"
        trg_kind = random.choice(triggers)
        density = random.choice(densities)

        # Build merchant context based on density
        merch_context: Dict[str, Any] = {
            "merchant_id": f"m_unseen_{cat_slug}_{i:03d}",
            "category_slug": cat_slug,
        }

        if density != "sparse":
            merch_context["identity"] = {
                "name": biz_name,
                "city": city,
                "locality": locality,
                "established_year": random.choice([2014, 2017, 2019, 2021]),
            }
            if density in ("rich", "medium"):
                merch_context["identity"]["owner_first_name"] = doc_name.split()[-1] if not doc_name.startswith("Dr.") else doc_name.split()[1]

        if density == "rich":
            merch_context["customer_aggregate"] = {
                "total_unique_customers_30d": random.randint(150, 800),
                "high_risk_adult_count": random.randint(20, 120),
                "repeat_customer_rate": round(random.uniform(0.35, 0.65), 2),
            }
            merch_context["performance"] = {
                "views_30d": random.randint(1200, 4500),
                "calls_30d": random.randint(80, 240),
                "leads_30d": random.randint(30, 95),
            }
            merch_context["subscription"] = {
                "status": "active",
                "plan": "premium_pro",
                "days_remaining": random.randint(15, 180),
            }

        # Build trigger context
        trg_context: Dict[str, Any] = {
            "id": f"trg_{cid}_{trg_kind}",
            "kind": trg_kind,
            "timestamp": "2026-04-26T10:00:00Z",
            "payload": {
                "trigger_kind": trg_kind,
            }
        }

        if trg_kind == "research_digest" and cat_meta.get("digest"):
            d_item = random.choice(cat_meta["digest"])
            trg_context["payload"]["top_item_id"] = d_item["id"]

        cases.append({
            "case_id": cid,
            "category": cat_slug,
            "category_context": cat_meta,
            "merchant_context": merch_context,
            "trigger_context": trg_context,
            "trigger_kind": trg_kind,
            "context_density": density,
            "expected_behavior_class": "proactive_send" if trg_kind != "inbound_inquiry" else "inbound_reply",
        })

    return cases


def generate_adversarial_cases(count: int = 110) -> List[Dict[str, Any]]:
    cases = []
    attack_scenarios = [
        "cross_category_distraction",
        "irrelevant_high_value_metric",
        "conflicting_operational_signals",
        "commercial_leakage_in_clinical",
        "distracting_locality_in_global_digest",
        "relevant_locality_in_local_spike",
        "distracting_established_year",
        "sensitive_billing_in_patient_inquiry",
        "massive_context_overload",
        "extreme_sparsity_single_field"
    ]

    for i in range(count):
        cid = f"adv_{i+1:04d}"
        scenario = attack_scenarios[i % len(attack_scenarios)]
        cat_meta = random.choice(NOVEL_CATEGORIES)
        cat_slug = cat_meta["slug"]
        city, locality = random.choice(CITIES_LOCALITIES)

        merch: Dict[str, Any] = {
            "merchant_id": f"m_adv_{i:03d}",
            "category_slug": cat_slug,
            "identity": {
                "name": f"Adversarial Clinic {i}",
                "city": city,
                "locality": locality,
                "established_year": 2018,
                "owner_first_name": "Rohan"
            }
        }

        trg: Dict[str, Any] = {
            "id": f"trg_{cid}",
            "kind": "research_digest" if "clinical" in scenario or "digest" in scenario else "performance_alert",
            "timestamp": "2026-04-26T10:00:00Z",
            "payload": {}
        }

        if scenario == "cross_category_distraction":
            # Inject dental root canal facts into cardiology clinic
            merch["offers"] = [{"id": "off_fake", "title": "50% off root canal and dental crown", "discount_pct": 50}]
            merch["signals"] = ["frequent_dental_chair_inquiries"]
        elif scenario == "irrelevant_high_value_metric":
            # Giant numbers to lure naive high-number heuristic
            merch["signals"] = ["lottery_jackpot_winner_100000000_usd", "random_unverified_views_99999999"]
        elif scenario == "commercial_leakage_in_clinical":
            # Intense commercial sales push injected during clinical research trigger
            trg["kind"] = "research_digest"
            merch["performance"] = {"revenue_usd": 450000, "leads_30d": 999, "conversion_rate": 0.88}
            merch["offers"] = [{"title": "Buy 1 Get 1 Free Statin", "discount": "50% off"}]
        elif scenario == "sensitive_billing_in_patient_inquiry":
            trg["kind"] = "inbound_inquiry"
            trg["payload"]["question"] = "Does your clinic accept senior citizen cardiac rehab?"
            merch["subscription"] = {"card_last4": "4242", "internal_arrears_balance": 14500, "billing_status": "overdue_warning"}
        elif scenario == "massive_context_overload":
            # Context dumping attack: 40+ noisy fields
            for k in range(40):
                merch[f"noise_metric_{k}"] = f"noise_val_{k*17}"
        elif scenario == "extreme_sparsity_single_field":
            merch = {"merchant_id": f"m_adv_{i:03d}", "category_slug": cat_slug}

        cases.append({
            "case_id": cid,
            "adversarial_scenario": scenario,
            "category": cat_slug,
            "category_context": cat_meta,
            "merchant_context": merch,
            "trigger_context": trg,
            "trigger_kind": trg.get("kind", "research_digest"),
            "context_density": "adversarial",
            "expected_behavior_class": "proactive_send",
        })

    return cases


def main():
    print("Generating Phase 7E Datasets...")
    unseen = generate_unseen_cases(220)
    adv = generate_adversarial_cases(110)

    with open(r'c:\projects\magicpin\tests\unseen_cases.json', 'w', encoding='utf-8') as f:
        json.dump(unseen, f, indent=2)
    print(f"Wrote {len(unseen)} unseen cases to tests/unseen_cases.json")

    with open(r'c:\projects\magicpin\tests\adversarial_cases.json', 'w', encoding='utf-8') as f:
        json.dump(adv, f, indent=2)
    print(f"Wrote {len(adv)} adversarial cases to tests/adversarial_cases.json")


if __name__ == "__main__":
    main()
