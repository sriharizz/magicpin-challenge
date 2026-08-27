"""
Final Stabilization Phase: Evidence-Driven Runtime Audit of 30+ Unseen Combinations.

Evaluates 30+ novel, diverse scenarios across healthcare, veterinary, fitness, hospitality,
retail, and professional services to forensically isolate genuine Stage-J composition defects:
1. Audience phrase noun-clashing (e.g. "delivery customers patients", "senior dogs patients")
2. Under-utilization of structurally available `actionable` guidance in CTA
3. Graceful handling of missing owner identity without hallucination

Zero benchmark-specific rules, zero category whitelists, zero hardcoded test IDs.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.store.context_store import get_context_store
from app.engine.composer import compose_research_digest
from app.relevance.general_selector import GeneralRelevanceSelector
from scripts.judge_score_forensics import evaluate_case_quality_score

client = TestClient(app)

# 30+ Genuinely Unseen Scenario Combinations
UNSEEN_35_SCENARIOS = [
    # Group 1: Non-Clinical Demographic Nouns (Testing Plural Clashing)
    {"id": "uns_01", "cat": "restaurants", "name": "Bhojan Express", "owner": "Aditi", "seg": "delivery customers", "n": 840, "src": "Food Logistics India Q2 2026", "act": "Adopt moisture-lock thermal containers", "title": "Packaging thermal retention in multi-drop deliveries"},
    {"id": "uns_02", "cat": "gyms", "name": "Iron Pulse Fitness", "owner": "Karan", "seg": "new members", "n": 350, "src": "Fitness Business Journal May 2026", "act": "Implement 14-day trainer check-in schedule", "title": "Onboarding touchpoints and member churn reduction"},
    {"id": "uns_03", "cat": "salons", "name": "Luxe Hair Studio", "owner": "Reema", "seg": "color clients", "n": 420, "src": "Salon Professional India Apr 2026", "act": "Pre-treat with bond-building peptide rinse", "title": "Peptide complex efficacy during oxidative coloring"},
    {"id": "uns_04", "cat": "pet_care", "name": "Paws & Tails Vet Clinic", "owner": "Dr. Sameer", "seg": "senior dogs", "n": 560, "src": "Veterinary Practice India Jun 2026", "act": "Screen with early renal biomarker panels", "title": "Early SDMA biomarker screening in aging canines"},
    {"id": "uns_05", "cat": "optometry", "name": "ClearVision Opticians", "owner": "Manish", "seg": "screen users", "n": 1100, "src": "Indian Journal of Optometry 2026", "act": "Recommend 20-20-20 rule plus blue-attenuation lenses", "title": "Digital asthenopia reduction in remote workers"},
    {"id": "uns_06", "cat": "spa_wellness", "name": "Ananda Wellness", "owner": "Pooja", "seg": "chronic stress clients", "n": 290, "src": "Integrative Health Review 2026", "act": "Integrate 20-minute guided diaphragmatic breathing", "title": "Cortisol attenuation via standardized Shirodhara protocols"},
    {"id": "uns_07", "cat": "auto_care", "name": "Apex Auto Care", "owner": "Harish", "seg": "fleet owners", "n": 780, "src": "Commercial Fleet India 2026", "act": "Switch to synthetic heavy-duty transmission fluid", "title": "Predictive maintenance intervals in urban delivery vans"},
    {"id": "uns_08", "cat": "coworking", "name": "Urban Hive Spaces", "owner": "Vikram", "seg": "remote workers", "n": 620, "src": "Modern Workplace Studies 2026", "act": "Equip flex-desks with dual ergonomic monitor arms", "title": "Ergonomic workspace layout and posture fatigue metrics"},

    # Group 2: Clinical Adjective Segments (Testing Correct "patients" Attachment)
    {"id": "uns_09", "cat": "dentists", "name": "Apex Dental Care", "owner": "Dr. Vivek", "seg": "high_risk_adults", "n": 2400, "src": "JIDA May 2026, p.22", "act": "Shorten recall interval to 3 months for high-risk decay cases", "title": "High-viscosity GIC in root caries recurrence prevention"},
    {"id": "uns_10", "cat": "cardiology", "name": "Heartline Institute", "owner": "Dr. Meenakshi", "seg": "hypertensive", "n": 14500, "src": "Indian Heart Journal Apr 2026", "act": "Transition uncontrolled hypertensives to single-pill dual combinations", "title": "Single-pill triple combinations in resistant hypertension"},
    {"id": "uns_11", "cat": "dermatology", "name": "Skin Excellence Clinic", "owner": "Dr. Neha", "seg": "atopic eczema", "n": 1850, "src": "Indian Journal of Dermatology 2026", "act": "Initiate proactive twice-weekly maintenance topical therapy", "title": "Proactive topical calcineurin inhibitors in recurrent atopic dermatitis"},
    {"id": "uns_12", "cat": "pediatrics", "name": "Little Stars Clinic", "owner": "Dr. Alok", "seg": "asthmatic pediatric", "n": 3200, "src": "Indian Pediatrics May 2026", "act": "Prescribe valved holding chambers with all metered dose inhalers", "title": "Valved holding chamber adherence in childhood asthma control"},
    {"id": "uns_13", "cat": "orthopedics", "name": "Orthocare Specialists", "owner": "Dr. Sanjay", "seg": "post operative knee", "n": 950, "src": "Journal of Arthroscopy India 2026", "act": "Initiate day-zero passive range of motion protocols", "title": "Early accelerated kinetic rehab post ACL reconstruction"},
    {"id": "uns_14", "cat": "ophthalmology", "name": "Netra Eye Center", "owner": "Dr. Radhika", "seg": "glaucoma suspect", "n": 4800, "src": "Ophthalmology Times India 2026", "act": "Perform baseline 24-2 visual field and macular OCT mapping", "title": "Progression detection rates with macular ganglion cell analysis"},
    {"id": "uns_15", "cat": "oncology", "name": "OncoShield Care", "owner": "Dr. Chetan", "seg": "neutropenic", "n": 1250, "src": "Indian Journal of Medical Oncology 2026", "act": "Administer prophylactic G-CSF on day two of myelosuppressive cycles", "title": "Prophylactic pegfilgrastim in solid tumor chemotherapy regimens"},
    {"id": "uns_16", "cat": "physiotherapy", "name": "Movement First Rehab", "owner": "Tarun", "seg": "chronic lower back", "n": 1400, "src": "Indian Spine Journal 2026", "act": "Prescribe progressive lumbar stabilization exercises 3x weekly", "title": "Lumbar motor control training versus general aerobic exercise"},

    # Group 3: Missing Identity Data (Testing Graceful Fallback Without Fabrication)
    {"id": "uns_17", "cat": "dentists", "name": "Smile Craft Dental", "owner": None, "seg": "periodontal", "n": 1600, "src": "Journal of Periodontology India 2026", "act": "Incorporate subgingival erythritol air polishing", "title": "Air polishing versus ultrasonic debridement in maintenance therapy"},
    {"id": "uns_18", "cat": "restaurants", "name": "Urban Tandoor", "owner": "", "seg": "dine-in guests", "n": 450, "src": "Restaurant Operations India 2026", "act": "Implement digital QR table ordering for beverage re-orders", "title": "Digital tabletop re-ordering and beverage attachment rates"},
    {"id": "uns_19", "cat": "salons", "name": "Style Lounge", "owner": None, "seg": "keratin clients", "n": 380, "src": "Hair Stylist Quarterly 2026", "act": "Use formaldehyde-free glyoxylic acid smoothing systems", "title": "Air quality and cuticle integrity during thermo-smoothing"},
    {"id": "uns_20", "cat": "pet_care", "name": "Pet Health First", "owner": None, "seg": "feline geriatric", "n": 720, "src": "Feline Medicine India 2026", "act": "Perform annual blood pressure checks on cats over seven years", "title": "Systemic hypertension prevalence in senior domestic felines"},

    # Group 4: Rich Actionable Guidance Utilization
    {"id": "uns_21", "cat": "pharmacies", "name": "MedPlus Chemist", "owner": "Deepak", "seg": "diabetic", "n": 5200, "src": "Pharmacy Practice India 2026", "act": "Flag potential metformin-induced B12 deficiency on refills over 12 months", "title": "Routine B12 monitoring in long-term metformin users"},
    {"id": "uns_22", "cat": "dentists", "name": "City Dental Clinic", "owner": "Dr. Anita", "seg": "pediatric caries", "n": 3400, "src": "Pediatric Dental Journal 2026", "act": "Apply 5% sodium fluoride varnish semi-annually in primary dentition", "title": "Fluoride varnish application frequency and dmft reduction"},
    {"id": "uns_23", "cat": "gyms", "name": "CrossFit Alpha", "owner": "Raghav", "seg": "strength athletes", "n": 820, "src": "Strength Conditioning India 2026", "act": "Program deload microcycles every four to six weeks", "title": "Scheduled deload weeks and chronic tendon overuse injuries"},
    {"id": "uns_24", "cat": "audiology", "name": "SoundClear Hearing", "owner": "Bhavna", "seg": "presbycusis adults", "n": 1900, "src": "Indian Journal of Otolaryngology 2026", "act": "Verify hearing aid fittings with real-ear measurement (REM)", "title": "Real-ear verification and patient satisfaction with digital hearing aids"},

    # Group 5: Sparse Context / Missing Actionable or Missing Sample Size
    {"id": "uns_25", "cat": "dentists", "name": "Premier Smiles", "owner": "Dr. Gaurav", "seg": "general", "n": None, "src": "Dental Tribune India 2026", "act": None, "title": "Overview of digital impression scanners in multi-chair clinics"},
    {"id": "uns_26", "cat": "restaurants", "name": "Curry Kingdom", "owner": "Suresh", "seg": None, "n": 510, "src": "Food Tech Review 2026", "act": "Audit delivery aggregator kitchen prep time metrics", "title": "Kitchen prep time variance and customer re-order rates"},
    {"id": "uns_27", "cat": "salons", "name": "Glamour Hub", "owner": "Ishita", "seg": "all", "n": None, "src": "Beauty Trends 2026", "act": None, "title": "Seasonal scalp hydration treatments in high-pollution cities"},
    {"id": "uns_28", "cat": "optometry", "name": "Focus Optical", "owner": "Nitin", "seg": "presbyopic", "n": 2200, "src": "Vision Science India 2026", "act": "Demonstrate progressive corridor widths using digital fitting tablets", "title": "Freeform progressive corridor customization and adaptation times"},

    # Group 6: Diverse Honorifics and Salutation Dialects
    {"id": "uns_29", "cat": "gyms", "name": "Vanguard Fitness", "owner": "Aditya", "seg": "weight loss members", "n": 950, "src": "Fitness India 2026", "act": "Combine progressive resistance training with protein pacing", "title": "Fat-free mass preservation during caloric restriction"},
    {"id": "uns_30", "cat": "pet_care", "name": "Companion Care Clinic", "owner": "Dr. Shruti", "seg": "brachycephalic breeds", "n": 410, "src": "Canine Respiratory Journal 2026", "act": "Perform pre-anesthetic airway assessments for brachycephalic pets", "title": "BOAS grading and perioperative respiratory complications"},
    {"id": "uns_31", "cat": "orthopedics", "name": "Spine & Joint Care", "owner": "Dr. Harsh", "seg": "osteoporotic", "n": 8900, "src": "Bone Joint India 2026", "act": "Prescribe annual zoledronic acid infusions post fragility fracture", "title": "Secondary fracture prevention with intravenous bisphosphonates"},
    {"id": "uns_32", "cat": "dentists", "name": "Zenith Dental", "owner": "Dr. Maya", "seg": "bruxism adults", "n": 1350, "src": "Prosthodontic Society 2026", "act": "Fabricate 3D-printed hard-soft occlusal splints for sleep bruxers", "title": "3D printed versus vacuum formed occlusal splint durability"},
    {"id": "uns_33", "cat": "restaurants", "name": "Dhaba 1947", "owner": "Karanveer", "seg": "buffet patrons", "n": 670, "src": "Hospitality Management 2026", "act": "Implement batch cooking schedules to minimize display holding times", "title": "Hot-holding temperature control and buffet food wastage"},
    {"id": "uns_34", "cat": "physiotherapy", "name": "Peak Mobility", "owner": "Preeti", "seg": "frozen shoulder", "n": 780, "src": "Physical Therapy India 2026", "act": "Perform glenohumeral capsular distension combined with high-grade mobilization", "title": "Hydrodilatation combined with supervised physical therapy in adhesive capsulitis"},
    {"id": "uns_35", "cat": "dermatology", "name": "ClearSkin Laser Clinic", "owner": "Dr. Varun", "seg": "melasma adults", "n": 1150, "src": "Pigmentary Disorders 2026", "act": "Prescribe oral tranexamic acid 250mg twice daily with broad-spectrum tinted sunscreen", "title": "Oral tranexamic acid adjunct in refractory recalcitrant melasma"},
]


def run_35_case_runtime_evidence_audit():
    store = get_context_store()
    results = []

    total_cases = len(UNSEEN_35_SCENARIOS)
    count_50_50 = 0
    scores = []
    
    loss_classification_counts = {
        "INPUT_DATA": 0,
        "EXTRACTION": 0,
        "RELEVANCE_SELECTION": 0,
        "CONTEXT_BUDGET": 0,
        "LLM": 0,
        "COMPOSER": 0,
        "VALIDATOR": 0,
        "STATE_MACHINE": 0,
        "EVALUATOR/HARNESS": 0,
    }

    defect_vs_artifact_counts = {
        "REAL_PRODUCT_DEFECT": 0,
        "EVALUATOR_HARNESS_ARTIFACT": 0,
        "INPUT_LIMITATION": 0,
    }

    repeated_patterns = {
        "PLURAL_NOUN_CLASH": 0,
        "GENERIC_CTA_WHEN_ACTIONABLE_AVAILABLE": 0,
        "MISSING_OWNER_NAME_FALLBACK": 0,
    }

    print("=" * 80)
    print(f"EVIDENCE-DRIVEN RUNTIME AUDIT OF {total_cases} GENUINELY UNSEEN COMBINATIONS")
    print("=" * 80)

    for idx, sc in enumerate(UNSEEN_35_SCENARIOS, start=1):
        store.clear()
        
        cid = sc["id"]
        cat_slug = sc["cat"]
        biz_name = sc["name"]
        owner_name = sc["owner"]
        seg = sc["seg"]
        trial_n = sc["n"]
        src = sc["src"]
        act = sc["act"]
        title = sc["title"]

        is_clinical = cat_slug in ("dentists", "cardiology", "dermatology", "pediatrics", "orthopedics", "ophthalmology", "oncology", "physiotherapy")
        salutation_example = "Dr. {first_name}" if is_clinical else "Hi {first_name}"

        # 1. Build Category Context
        category_payload = {
            "slug": cat_slug,
            "display_name": cat_slug.capitalize(),
            "voice": {
                "tone": "peer_clinical" if is_clinical else "operator_to_operator",
                "vocab_taboo": ["guaranteed cure", "100% safe", "miracle"],
                "salutation_examples": [salutation_example],
            },
            "digest": [
                {
                    "id": f"d_{cid}",
                    "kind": "research",
                    "title": title,
                    "source": src,
                    "trial_n": trial_n,
                    "patient_segment": seg,
                    "summary": f"Multi-center clinical evaluation showed 42% improved outcomes across primary cohorts ({title}).",
                    "actionable": act,
                }
            ],
            "patient_content_library": [{"id": f"pc_{cid}", "title": "Clinical Brief", "body": "Guideline summary for patients."}] if is_clinical else [],
        }

        # 2. Build Merchant Context
        merchant_payload = {
            "merchant_id": f"m_{cid}",
            "category_slug": cat_slug,
            "identity": {
                "name": biz_name,
                "owner_first_name": owner_name,
                "city": "Bengaluru",
                "locality": "Indiranagar",
            },
            "subscription": {"status": "active", "plan": "Pro", "days_remaining": 120},
            "customer_aggregate": {"target_cohort_count": 180, "total_unique_ytd": 850},
            "signals": [],
            "conversation_history": [],
        }

        # 3. Build Trigger Context
        trigger_payload = {
            "id": f"trg_{cid}",
            "scope": "merchant",
            "kind": "guideline_alert",
            "merchant_id": f"m_{cid}",
            "payload": {"top_item_id": f"d_{cid}", "category": cat_slug},
            "urgency": 2,
            "suppression_key": f"trg:{cat_slug}:{cid}",
            "expires_at": "2026-12-31T00:00:00Z",
        }

        # Ingest
        client.post("/v1/context", json={"scope": "category", "context_id": cat_slug, "version": 1, "payload": category_payload, "delivered_at": "2026-04-26T10:00:00Z"})
        client.post("/v1/context", json={"scope": "merchant", "context_id": f"m_{cid}", "version": 1, "payload": merchant_payload, "delivered_at": "2026-04-26T10:00:00Z"})
        client.post("/v1/context", json={"scope": "trigger", "context_id": f"trg_{cid}", "version": 1, "payload": trigger_payload, "delivered_at": "2026-04-26T10:00:00Z"})

        # Execute Live API /v1/tick
        r_tick = client.post("/v1/tick", json={"now": "2026-04-26T10:30:00Z", "available_triggers": [f"trg_{cid}"]})
        tick_data = r_tick.json()
        actions = tick_data.get("actions", [])
        emitted_body = actions[0].get("body", "") if actions else ""
        emitted_cta = actions[0].get("cta", "none") if actions else "none"

        # Evaluate Quality Score
        score, dim_scores, reasons, deductions = evaluate_case_quality_score(
            category=category_payload,
            merchant=merchant_payload,
            trigger=trigger_payload,
            body=emitted_body,
            cta=emitted_cta
        )

        scores.append(score)
        if score == 50:
            count_50_50 += 1

        # Detect specific linguistic patterns
        has_noun_clash = False
        if seg:
            lower_seg = seg.lower()
            if any(noun in lower_seg for noun in ["customers", "members", "clients", "dogs", "canines", "users", "patrons", "workers", "owners"]):
                if "patients" in emitted_body and lower_seg in emitted_body:
                    has_noun_clash = True
                    repeated_patterns["PLURAL_NOUN_CLASH"] += 1

        has_generic_cta = False
        if act and "Want me to pull the key takeaways for your team?" in emitted_body:
            has_generic_cta = True
            repeated_patterns["GENERIC_CTA_WHEN_ACTIONABLE_AVAILABLE"] += 1

        is_missing_owner = False
        if not owner_name:
            is_missing_owner = True
            repeated_patterns["MISSING_OWNER_NAME_FALLBACK"] += 1

        # Classify point loss
        primary_loss_stage = "NONE"
        defect_type = "NONE"

        if deductions:
            for ded in deductions:
                stg = ded["stage_candidate"]
                if stg == "A_UPSTREAM_MISSING":
                    loss_classification_counts["INPUT_DATA"] += ded["points_lost"]
                    primary_loss_stage = "INPUT_DATA"
                    defect_type = "INPUT_LIMITATION"
                elif stg == "J_OUTPUT_COMPOSER":
                    loss_classification_counts["COMPOSER"] += ded["points_lost"]
                    primary_loss_stage = "COMPOSER"
                    defect_type = "REAL_PRODUCT_DEFECT"
                elif stg == "D_RELEVANCE_SCORING":
                    loss_classification_counts["RELEVANCE_SELECTION"] += ded["points_lost"]
                    primary_loss_stage = "RELEVANCE_SELECTION"
                    defect_type = "REAL_PRODUCT_DEFECT"

            if defect_type == "REAL_PRODUCT_DEFECT":
                defect_vs_artifact_counts["REAL_PRODUCT_DEFECT"] += 1
            elif defect_type == "INPUT_LIMITATION":
                defect_vs_artifact_counts["INPUT_LIMITATION"] += 1

        case_record = {
            "case_id": cid,
            "category": cat_slug,
            "business_name": biz_name,
            "owner_name": owner_name or "[MISSING UPSTREAM]",
            "segment": seg or "[NONE]",
            "trial_n": trial_n or "[NONE]",
            "actionable_provided": act or "[NONE]",
            "emitted_body": emitted_body,
            "score": score,
            "dim_scores": dim_scores,
            "deductions": deductions,
            "first_stage_responsible": primary_loss_stage,
            "defect_classification": defect_type,
            "patterns_observed": {
                "plural_noun_clash": has_noun_clash,
                "generic_cta_despite_actionable": has_generic_cta,
                "missing_owner_fallback": is_missing_owner,
            }
        }
        results.append(case_record)

        print(f"[{idx:02d}/35] Case: {cid} | Cat: {cat_slug:<12} | Score: {score}/50 | Stage: {primary_loss_stage:<10} | NounClash: {has_noun_clash} | GenCTA: {has_generic_cta}")
        print(f"     Body: \"{emitted_body}\"")

    out_file = Path(__file__).parent.parent / "docs" / "runtime_evidence_audit_35_cases.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_cases": total_cases,
            "count_50_50": count_50_50,
            "avg_score": round(sum(scores) / total_cases, 2),
            "worst_score": min(scores),
            "loss_stage_breakdown": loss_classification_counts,
            "defect_vs_artifact_counts": defect_vs_artifact_counts,
            "repeated_patterns": repeated_patterns,
            "cases": results
        }, f, indent=2)

    print("\n" + "=" * 80)
    print("RUNTIME EVIDENCE AUDIT SUMMARY (35 UNSEEN SCENARIOS)")
    print("=" * 80)
    print(f"Total Cases Evaluated   : {total_cases}")
    print(f"Cases Scoring 50/50     : {count_50_50} ({count_50_50/total_cases*100:.1f}%)")
    print(f"Average Score           : {sum(scores)/total_cases:.2f} / 50")
    print(f"Worst Score             : {min(scores)} / 50")
    print("\nLoss Classification Breakdown (Points Lost):")
    for stg, pts in loss_classification_counts.items():
        if pts > 0:
            print(f"  {stg:<22} : {pts:>3} points lost")
    print("\nRepeated Linguistic & Composition Patterns:")
    print(f"  Plural Noun Clashing (e.g. 'delivery customers patients') : {repeated_patterns['PLURAL_NOUN_CLASH']} cases")
    print(f"  Generic CTA despite structured `actionable` available    : {repeated_patterns['GENERIC_CTA_WHEN_ACTIONABLE_AVAILABLE']} cases")
    print(f"  Upstream Missing Owner Name Fallback                      : {repeated_patterns['MISSING_OWNER_NAME_FALLBACK']} cases")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_35_case_runtime_evidence_audit()
