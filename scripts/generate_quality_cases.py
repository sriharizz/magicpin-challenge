import json
import random
from pathlib import Path

# Seed for deterministic generation
random.seed(42)

CATEGORIES = {
    "dentists": {
        "slug": "dentists",
        "voice": {
            "tone": "peer_clinical",
            "register": "respectful_collegial",
            "code_mix": "hindi_english_natural",
            "vocab_allowed": ["caries", "fluoride varnish", "scaling", "occlusion", "IOPA", "RCT", "GIC"],
            "vocab_taboo": ["guaranteed", "100% safe", "completely cure", "miracle", "best in city"]
        },
        "digest": [
            {
                "id": "d_dent_01",
                "title": "High-viscosity GIC in root caries",
                "source": "JIDA Oct 2026, p.14",
                "trial_n": 2100,
                "patient_segment": "high_risk_adults",
                "summary": "Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history.",
                "actionable": "Reassess recall interval for adults flagged high-risk in your charting"
            },
            {
                "id": "d_dent_02",
                "title": "CBCT vs OPG in impacted third molar assessment",
                "source": "Indian Journal of Dental Research Nov 2026",
                "trial_n": 950,
                "patient_segment": "surgical_cases",
                "summary": "Pre-op CBCT reduced inferior alveolar nerve injury by 44% in high-difficulty impactions.",
                "actionable": "Adopt 3D imaging protocols for deep impactions"
            }
        ]
    },
    "gyms": {
        "slug": "gyms",
        "voice": {
            "tone": "coaching_motivational",
            "register": "direct_energetic",
            "code_mix": "hindi_english_natural",
            "vocab_allowed": ["hypertrophy", "progressive overload", "retention", "walk-in", "body comp", "plateau"],
            "vocab_taboo": ["guaranteed weight loss", "100% transformation", "melt fat", "magic pill"]
        },
        "digest": [
            {
                "id": "d_gym_01",
                "title": "Seasonal Acquisition Dip & Retention Strategies",
                "source": "Fitness Business India Q2 2026",
                "trial_n": 420,
                "patient_segment": "new_members",
                "summary": "Gym walk-ins drop 32% in Q2. Facilities running structured 30-day onboarding retain 54% more members into Q3.",
                "actionable": "Launch 30-day onboarding habit challenge"
            }
        ]
    },
    "pharmacies": {
        "slug": "pharmacies",
        "voice": {
            "tone": "trustworthy_precise",
            "register": "professional_care",
            "code_mix": "hindi_english_natural",
            "vocab_allowed": ["refill", "chronic care", "compliance", "margin", "generic", "cold chain"],
            "vocab_taboo": ["cure all", "100% cure", "instant relief", "miracle cure"]
        },
        "digest": [
            {
                "id": "d_pharm_01",
                "title": "DGCI SR-Formulation Price Revision",
                "source": "DGCI Circular Apr 2026",
                "trial_n": 1500,
                "patient_segment": "chronic_diabetic",
                "summary": "Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended.",
                "actionable": "Notify chronic patients about price relief + stock up"
            }
        ]
    },
    "restaurants": {
        "slug": "restaurants",
        "voice": {
            "tone": "operator_to_operator",
            "register": "pragmatic_business",
            "code_mix": "hindi_english_natural",
            "vocab_allowed": ["table turn", "average order value", "covers", "food cost", "swiggy/zomato commission"],
            "vocab_taboo": ["best food in world", "guaranteed crowd", "100% fresh always"]
        },
        "digest": [
            {
                "id": "d_rest_01",
                "title": "Pre-monsoon Delivery Packaging & AOV",
                "source": "NRAI Quarterly Brief May 2026",
                "trial_n": 680,
                "patient_segment": "delivery_customers",
                "summary": "Vented tamper-proof boxes improved crispy item delivery ratings by 0.6 stars and cut refund requests by 41%.",
                "actionable": "Upgrade delivery packaging before monsoon"
            }
        ]
    },
    "salons": {
        "slug": "salons",
        "voice": {
            "tone": "warm_practical",
            "register": "friendly_expert",
            "code_mix": "hindi_english_natural",
            "vocab_allowed": ["bond repair", "balayage", "bridal trial", "rebooking", "stylist utilization"],
            "vocab_taboo": ["zero hairfall guaranteed", "100% permanent glow", "miracle skin"]
        },
        "digest": [
            {
                "id": "d_sal_01",
                "title": "Pre-shampoo Bond Protector in Chemical Hair Treatment",
                "source": "Hair Brand News India Apr 2026",
                "trial_n": 520,
                "patient_segment": "color_clients",
                "summary": "Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures.",
                "actionable": "Introduce express bond-repair add-on"
            }
        ]
    },
    "optometry": {
        "slug": "optometry",
        "voice": {
            "tone": "clinical_vision_care",
            "register": "precise_collegial",
            "code_mix": "hindi_english_natural",
            "vocab_allowed": ["myopia control", "ortho-k", "blue filter", "fundus screening", "astigmatism", "diopters"],
            "vocab_taboo": ["cure blindness", "100% eyesight restoration", "throw glasses away"]
        },
        "digest": [
            {
                "id": "d_opt_01",
                "title": "Low-dose Atropine 0.01% in Pediatric Myopia Progression",
                "source": "Indian Journal of Ophthalmology May 2026",
                "trial_n": 1200,
                "patient_segment": "pediatric_myopia",
                "summary": "Nightly 0.01% atropine drops combined with outdoor time slowed axial elongation by 51% over 24 months in school-age children.",
                "actionable": "Implement pediatric myopia tracking protocol"
            }
        ]
    },
    "physiotherapy": {
        "slug": "physiotherapy",
        "voice": {
            "tone": "rehab_clinical",
            "register": "evidence_based_care",
            "code_mix": "hindi_english_natural",
            "vocab_allowed": ["biomechanics", "dry needling", "ROM", "proprioception", "lumbar radiculopathy", "isokinetic"],
            "vocab_taboo": ["cure paralysis in 1 day", "100% pain free forever", "magic adjustment"]
        },
        "digest": [
            {
                "id": "d_phys_01",
                "title": "Early eccentric loading in chronic patellar tendinopathy",
                "source": "Journal of Orthopaedic & Sports Physical Therapy Jun 2026",
                "trial_n": 480,
                "patient_segment": "athletic_rehab",
                "summary": "Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities.",
                "actionable": "Update patellar tendinopathy exercise prescription"
            }
        ]
    },
    "pet_care": {
        "slug": "pet_care",
        "voice": {
            "tone": "compassionate_expert",
            "register": "pet_parent_partner",
            "code_mix": "hindi_english_natural",
            "vocab_allowed": ["deworming", "titer test", "dermatitis", "tick fever", "senior canine", "gastroenteritis"],
            "vocab_taboo": ["cure rabies", "100% flea free guarantee", "miracle pet cure"]
        },
        "digest": [
            {
                "id": "d_pet_01",
                "title": "Monoclonal antibody therapy in canine atopic dermatitis",
                "source": "Veterinary Dermatology India May 2026",
                "trial_n": 650,
                "patient_segment": "allergic_canines",
                "summary": "Monthly lokivetmab injections achieved 76% pruritus reduction with zero steroid-induced liver enzyme elevation in chronic atopic dogs.",
                "actionable": "Offer steroid-sparing biological options for atopic pets"
            }
        ]
    }
}

TRIGGER_KINDS = [
    "research_digest", "regulation_change", "recall_due", "perf_dip",
    "renewal_due", "festival_upcoming", "wedding_package_followup",
    "curious_ask_due", "winback_eligible", "review_theme_emerged",
    "milestone_reached", "supply_alert", "chronic_refill_due", "competitor_opened"
]

CITIES = ["Delhi", "Mumbai", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Jaipur", "Lucknow", "Chandigarh"]
LOCALITIES = ["Indiranagar", "Koramangala", "Lajpat Nagar", "Bandra West", "Jubilee Hills", "Anna Nagar", "Park Street", "C-Scheme", "Hazratganj", "Sector 17"]

OWNER_NAMES = [
    "Meera", "Bharat", "Rajan", "Pooja", "Karim", "Bharti", "Ananya", "Vikram",
    "Sneha", "Arjun", "Kavya", "Rahul", "Priya", "Sunil", "Ritu", "Deepak",
    "Amit", "Tanvi", "Siddharth", "Neha", "Manish", "Divya", "Suresh", "Tarun"
]

def generate_quality_cases(target_count=520):
    cases = []
    cat_keys = list(CATEGORIES.keys())
    
    for i in range(1, target_count + 1):
        case_id = f"qc_{i:04d}"
        cat_slug = cat_keys[(i - 1) % len(cat_keys)]
        cat_meta = CATEGORIES[cat_slug]
        
        # Density distribution: 35% rich, 35% medium, 20% sparse, 10% missing_optional
        density_roll = random.random()
        if density_roll < 0.35:
            density = "rich"
        elif density_roll < 0.70:
            density = "medium"
        elif density_roll < 0.90:
            density = "sparse"
        else:
            density = "missing_optional"
            
        # Difficulty: 40% normal, 30% medium, 20% hard, 10% adversarial_quality
        diff_roll = random.random()
        if diff_roll < 0.40:
            difficulty = "normal"
        elif diff_roll < 0.70:
            difficulty = "medium"
        elif diff_roll < 0.90:
            difficulty = "hard"
        else:
            difficulty = "adversarial_quality"

        owner_first = random.choice(OWNER_NAMES)
        city = random.choice(CITIES)
        locality = random.choice(LOCALITIES)
        merchant_id = f"m_{cat_slug[:4]}_{owner_first.lower()}_{i:03d}"
        
        # Build merchant identity based on density
        if density == "rich":
            identity = {
                "name": f"Dr. {owner_first}'s Clinic" if cat_slug in ["dentists", "optometry", "physiotherapy"] else f"{owner_first}'s {cat_slug.title()}",
                "owner_first_name": owner_first,
                "city": city,
                "locality": locality,
                "verified": True,
                "languages": ["en", "hi"],
                "established_year": random.randint(2012, 2022)
            }
            perf = {
                "window_days": 30,
                "views": random.randint(1200, 4500),
                "calls": random.randint(15, 80),
                "directions": random.randint(30, 120),
                "ctr": round(random.uniform(0.015, 0.045), 3),
                "leads": random.randint(8, 35)
            }
            signals = ["high_risk_cohort", "engaged_in_last_48h", "ctr_above_median"]
            cust_agg = {"total_unique_ytd": random.randint(400, 1200), "high_risk_adult_count": random.randint(60, 200)}
            offers = [{"id": f"o_{i}_01", "title": f"Special Consultation @ ₹299", "status": "active"}]
        elif density == "medium":
            identity = {
                "name": f"{owner_first}'s {cat_slug.title()}",
                "owner_first_name": owner_first,
                "city": city,
                "locality": locality,
                "verified": False,
                "languages": ["en"]
            }
            perf = {"window_days": 30, "views": random.randint(500, 1500), "calls": random.randint(5, 20), "ctr": 0.018}
            signals = ["stale_posts:18d"]
            cust_agg = {"total_unique_ytd": random.randint(150, 400)}
            offers = []
        elif density == "sparse":
            identity = {
                "name": f"{cat_slug.title()} Center",
                "owner_first_name": None if difficulty in ["hard", "adversarial_quality"] else owner_first,
                "city": city
            }
            perf = {"views": random.randint(100, 500)}
            signals = []
            cust_agg = {}
            offers = []
        else: # missing_optional
            identity = {"name": None, "owner_first_name": None}
            perf = {}
            signals = []
            cust_agg = {}
            offers = []

        merchant_ctx = {
            "merchant_id": merchant_id,
            "category_slug": cat_slug,
            "identity": identity,
            "subscription": {"status": "active", "plan": "Pro", "days_remaining": random.randint(15, 90)},
            "performance": perf,
            "signals": signals,
            "customer_aggregate": cust_agg,
            "offers": offers
        }
        
        # Trigger selection
        trg_kind = TRIGGER_KINDS[(i - 1) % len(TRIGGER_KINDS)]
        urgency = random.randint(1, 5)
        top_digest = cat_meta["digest"][0] if cat_meta["digest"] else None
        
        # Custom edge cases for difficulty
        if difficulty == "adversarial_quality":
            # e.g., expired trigger or conflicting context
            if i % 3 == 0:
                expires_at = "2026-04-20T00:00:00Z" # Expired
                exp_class = "suppress_expired"
                reason = "Expired trigger payload — Vera must not emit ungrounded action"
            elif i % 3 == 1:
                expires_at = "2026-05-30T00:00:00Z"
                exp_class = "proactive_send"
                reason = "High-specificity cohort alignment on clinical finding"
            else:
                expires_at = "2026-05-30T00:00:00Z"
                exp_class = "proactive_send"
                reason = "Sparse merchant identity with rich clinical evidence"
        else:
            expires_at = "2026-05-30T00:00:00Z"
            exp_class = "proactive_send"
            reason = f"Standard {trg_kind} scenario for {cat_slug} ({density} context)"

        trg_ctx = {
            "id": f"trg_{case_id}_{trg_kind}",
            "scope": "merchant",
            "kind": trg_kind,
            "merchant_id": merchant_id,
            "payload": {
                "category": cat_slug,
                "top_item_id": top_digest["id"] if top_digest else None,
                "urgency_score": urgency
            },
            "urgency": urgency,
            "suppression_key": f"{trg_kind}:{cat_slug}:{i}",
            "expires_at": expires_at
        }

        facts = [
            f"Category is {cat_slug}",
            f"Tone is {cat_meta['voice']['tone']}",
            f"Digest source: {top_digest['source'] if top_digest else 'Industry Report'}",
            f"Trial size: {top_digest['trial_n'] if top_digest else 'N/A'}",
            f"Key takeaway: {top_digest['summary'] if top_digest else 'N/A'}"
        ]

        cases.append({
            "case_id": case_id,
            "category": cat_slug,
            "merchant_context": merchant_ctx,
            "category_context": cat_meta,
            "trigger_context": trg_ctx,
            "customer_context": None,
            "trigger_kind": trg_kind,
            "context_density": density,
            "urgency": urgency,
            "available_facts": facts,
            "expected_behavior_class": exp_class,
            "difficulty": difficulty,
            "reason_for_case": reason
        })

    return cases

if __name__ == "__main__":
    cases = generate_quality_cases(520)
    out_path = Path(r"c:\projects\magicpin\tests\quality_cases.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    print(f"Successfully generated {len(cases)} synthetic quality evaluation cases at {out_path}")
