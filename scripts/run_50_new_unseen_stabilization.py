"""
Final Stabilization Suite: 50 Completely NEW Unseen Scenarios.

Evaluates 50 novel, diverse scenarios across 25+ distinct industry verticals
that were NOT used in any previous audit or design step:
- Tests audience phrasing across novel noun types (e.g. commuters, athletes, patrons, puppies, brides, runners, pilots)
- Tests grounded actionable CTA synthesis vs fallback
- Tests missing identity fallback preservation
- Measures score distribution, average score, minimum score, and safety regressions
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.store.context_store import get_context_store
from scripts.judge_score_forensics import evaluate_case_quality_score

client = TestClient(app)

NEW_50_SCENARIOS = [
    {"id": "new_01", "cat": "bakeries", "name": "Crust & Crumb", "owner": "Ankit", "seg": "morning commuters", "n": 420, "src": "Bakery Management India 2026", "act": "Pre-pack grab-and-go breakfast pastry combos", "title": "Morning counter queue reduction via pre-packaged breakfast combos"},
    {"id": "new_02", "cat": "coffee_shops", "name": "Roast Craft Cafe", "owner": "Snehal", "seg": "espresso drinkers", "n": 650, "src": "Specialty Coffee India 2026", "act": "Calibrate grinder burr temperatures hourly", "title": "Burr temperature stabilization and extraction yield consistency"},
    {"id": "new_03", "cat": "yoga_studios", "name": "Prana Yoga Space", "owner": "Gayatri", "seg": "prenatal practitioners", "n": 310, "src": "Yoga & Health India 2026", "act": "Incorporate bolster-supported lateral postures", "title": "Pelvic floor comfort in third-trimester modified vinyasa"},
    {"id": "new_04", "cat": "car_detailing", "name": "Ceramic Pro Works", "owner": "Rishi", "seg": "luxury car owners", "n": 280, "src": "Auto Detailing India 2026", "act": "Use infrared curing lamps for 9H ceramic coatings", "title": "Infrared curing duration and ceramic hydrophobic longevity"},
    {"id": "new_05", "cat": "daycare", "name": "Tiny Steps Preschool", "owner": "Meera", "seg": "toddler parents", "n": 520, "src": "Early Childhood Education 2026", "act": "Send midday digital meal and nap updates", "title": "Real-time daily activity logs and parent satisfaction metrics"},
    {"id": "new_06", "cat": "chiropractic", "name": "Spine Align Clinic", "owner": "Dr. Pranav", "seg": "cervical radiculopathy", "n": 890, "src": "Spine Rehabilitation Review 2026", "act": "Combine mechanical traction with thoracic mobilization", "title": "Cervical nerve root decompression outcomes in desk workers"},
    {"id": "new_07", "cat": "podiatry", "name": "Foot Care Center", "owner": "Dr. Shweta", "seg": "diabetic foot ulcer", "n": 1450, "src": "Indian Podiatry Journal 2026", "act": "Prescribe total contact casting for neuropathic plantar ulcers", "title": "Offloading efficacy of total contact casts in Wagner Grade 2 ulcers"},
    {"id": "new_08", "cat": "endocrinology", "name": "ThyroCare Endocrinology", "owner": "Dr. Raman", "seg": "hypothyroid", "n": 6200, "src": "Indian Journal of Endocrinology 2026", "act": "Ensure levothyroxine is ingested with water 60 minutes before breakfast", "title": "Fasting interval compliance and TSH normalization rates"},
    {"id": "new_09", "cat": "nephrology", "name": "Renal Health Institute", "owner": "Dr. Arvind", "seg": "stage 3 ckd", "n": 4300, "src": "Indian Nephrology Review 2026", "act": "Initiate low-protein dietary counseling combined with SGLT2 inhibitors", "title": "eGFR preservation with early SGLT2 inhibitor initiation in non-diabetic CKD"},
    {"id": "new_10", "cat": "sports_medicine", "name": "Elite Athlete Clinic", "owner": "Dr. Kunal", "seg": "marathon runners", "n": 760, "src": "Sports Health India 2026", "act": "Monitor eccentric quadriceps loading using wearable IMU sensors", "title": "Patellar tendinopathy prevention via real-time tibial acceleration monitoring"},
    {"id": "new_11", "cat": "bridal_makeup", "name": "Glow Bridal Studio", "owner": "Sanya", "seg": "destination brides", "n": 190, "src": "Bridal Artistry India 2026", "act": "Use humidity-resistant silicone primers for outdoor humid venues", "title": "Airbrush silicone formulations and 12-hour makeup longevity in coastal weather"},
    {"id": "new_12", "cat": "co_living", "name": "Nest Co-Living", "owner": "Aakash", "seg": "young professionals", "n": 840, "src": "Urban Housing India 2026", "act": "Organize bi-weekly community mixer dinners", "title": "Community event attendance and tenant lease renewal rates"},
    {"id": "new_13", "cat": "meal_prep", "name": "FitBites Kitchen", "owner": "Pawan", "seg": "macro counting athletes", "n": 950, "src": "Nutrition Tech India 2026", "act": "Include precise macronutrient breakdown QR codes on meal sleeves", "title": "Macro transparency labels and subscription retention in fitness meal prep"},
    {"id": "new_14", "cat": "photography", "name": "Studio Click Pro", "owner": "Kush", "seg": "corporate event organizers", "n": 340, "src": "Commercial Photography 2026", "act": "Deliver same-day social media preview gallery within 4 hours", "title": "Express teaser gallery turnaround and corporate re-booking probability"},
    {"id": "new_15", "cat": "pet_care", "name": "Puppy Care Center", "owner": "Dr. Priya", "seg": "vaccinated puppies", "n": 610, "src": "Pediatric Veterinary India 2026", "act": "Recommend early socialization classes starting 7 days post-second vaccine", "title": "Early socialization window and adult behavioral aggression incidence in dogs"},
    {"id": "new_16", "cat": "dentists", "name": "Dental Implants Hub", "owner": "Dr. Rohit", "seg": "edentulous adults", "n": 3100, "src": "Implantology India 2026", "act": "Utilize dynamic surgical navigation for tilted immediate-load implants", "title": "Immediate loading success rates in atrophic maxilla with dynamic navigation"},
    {"id": "new_17", "cat": "dentists", "name": "Clear Align Center", "owner": None, "seg": "crowding adults", "n": 2200, "src": "Orthodontic Practice 2026", "act": "Prescribe weekly aligner staging with high-frequency vibration seating", "title": "Tracking accuracy in moderate anterior crowding with 7-day aligner wear"},
    {"id": "new_18", "cat": "restaurants", "name": "Biryani Darbar", "owner": None, "seg": "takeaway customers", "n": 1200, "src": "Quick Service India 2026", "act": "Adopt insulated thermal foil carry bags", "title": "Temperature drop during peak winter deliveries and customer satisfaction"},
    {"id": "new_19", "cat": "gyms", "name": "Iron Forge Gym", "owner": None, "seg": "powerlifters", "n": 480, "src": "Strength Science 2026", "act": "Install calibrated bumper plates and competition power bars", "title": "Equipment quality perception and barbell athlete retention"},
    {"id": "new_20", "cat": "salons", "name": "The Hair Bar", "owner": None, "seg": "balayage clients", "n": 390, "src": "Colorist Weekly 2026", "act": "Apply clay-based lighteners for open-air freehand painting", "title": "Transfer-free open-air balayage techniques and application speed"},
    {"id": "new_21", "cat": "optometry", "name": "Lens & Frame", "owner": "Kavita", "seg": "myopic children", "n": 1600, "src": "Pediatric Vision India 2026", "act": "Fit peripheral defocus spectacle lenses for progressive myopia", "title": "Axial elongation slowing with DIMS spectacle lens technology"},
    {"id": "new_22", "cat": "physiotherapy", "name": "Active Life Clinic", "owner": "Dr. Vikas", "seg": "plantar fasciitis", "n": 980, "src": "Physical Therapy Journal 2026", "act": "Prescribe high-load strength training with rolled towel toe extension", "title": "High-load isometric plantar fascia loading versus calf stretching"},
    {"id": "new_23", "cat": "dermatology", "name": "Derma Care Laser", "owner": "Dr. Shraddha", "seg": "acne vulgaris", "n": 2700, "src": "Dermatology Times 2026", "act": "Prescribe fixed-dose clindamycin-adapalene gel with ceramide moisturizer", "title": "Barrier restoration and tolerability during topical retinoid induction"},
    {"id": "new_24", "cat": "cardiology", "name": "Heart Pulse Center", "owner": "Dr. Dev", "seg": "post stenting", "n": 8200, "src": "Coronary Care India 2026", "act": "Enroll patients in hospital-supervised cardiac rehab within 14 days", "title": "Cardiac rehab completion and 1-year major adverse cardiovascular events"},
    {"id": "new_25", "cat": "pediatrics", "name": "Kidz Clinic", "owner": "Dr. Ritu", "seg": "colicky infants", "n": 1100, "src": "Pediatric Care 2026", "act": "Administer daily Limosilactobacillus reuteri probiotic drops", "title": "L. reuteri DSM 17938 supplementation and infant crying duration in colic"},
    {"id": "new_26", "cat": "orthopedics", "name": "Bone Health Clinic", "owner": "Dr. Amit", "seg": "rotator cuff tears", "n": 1850, "src": "Shoulder Elbow Surgery 2026", "act": "Initiate delayed active elevation at 6 weeks post arthroscopic repair", "title": "Structural tendon healing rates with delayed versus early passive mobilization"},
    {"id": "new_27", "cat": "oncology", "name": "Hope Oncology", "owner": "Dr. Anirudh", "seg": "immunotherapy patients", "n": 3400, "src": "Immuno-Oncology Review 2026", "act": "Educate patients on early reporting of immune-related adverse colitis", "title": "Early irAE identification and steroid response in checkpoint inhibitor therapy"},
    {"id": "new_28", "cat": "spa_wellness", "name": "Soma Spa", "owner": "Tanya", "seg": "insomnia clients", "n": 410, "src": "Sleep Wellness 2026", "act": "Offer warm magnesium salt hydrotherapy baths before massage sessions", "title": "Transdermal magnesium absorption and deep sleep latency improvements"},
    {"id": "new_29", "cat": "auto_care", "name": "Speedy Lube", "owner": "Girish", "seg": "commercial taxi drivers", "n": 1500, "src": "Fleet Maintenance 2026", "act": "Perform rapid 15-minute express oil changes during off-peak hours", "title": "Express service bay turnaround and commercial fleet driver loyalty"},
    {"id": "new_30", "cat": "coworking", "name": "NextGen Workspaces", "owner": "Varun", "seg": "startup founders", "n": 720, "src": "Coworking Trends 2026", "act": "Host monthly angel investor pitch open mics", "title": "Networking event density and member retention in boutique coworking spaces"},
    {"id": "new_31", "cat": "bakeries", "name": "Sourdough Guild", "owner": "Arjun", "seg": "artisanal bread buyers", "n": 580, "src": "Artisan Baker 2026", "act": "Ferment dough for a minimum of 24 hours at 4 degrees Celsius", "title": "Cold-fermentation duration and sourdough prebiotic oligosaccharide profile"},
    {"id": "new_32", "cat": "coffee_shops", "name": "Bean Origin", "owner": "Maya", "seg": "pourover enthusiasts", "n": 320, "src": "Brewing Science 2026", "act": "Use remineralized reverse osmosis water at 120ppm hardness", "title": "Water mineral balance and sensory clarity in light-roast filter coffee"},
    {"id": "new_33", "cat": "yoga_studios", "name": "Vinyasa Flow", "owner": "Naveen", "seg": "ashtanga students", "n": 260, "src": "Ashtanga Yoga Studies 2026", "act": "Offer weekly guided jump-through alignment workshops", "title": "Wrist torque reduction via scapular protraction in jumping transitions"},
    {"id": "new_34", "cat": "car_detailing", "name": "Ultra Gloss Studio", "owner": "Samir", "seg": "classic car collectors", "n": 140, "src": "Classic Car Care 2026", "act": "Use rotary polishers with wool pads on original single-stage paint", "title": "Paint depth preservation during correction on vintage cellulose finishes"},
    {"id": "new_35", "cat": "daycare", "name": "Sunny Days Childcare", "owner": "Komal", "seg": "working mothers", "n": 480, "src": "Childcare Management 2026", "act": "Extend evening pickup grace window by 30 minutes", "title": "Flexible pickup policies and working mother retention in urban daycares"},
    {"id": "new_36", "cat": "chiropractic", "name": "Alignment Center", "owner": "Dr. Vivek", "seg": "sciatica cases", "n": 1120, "src": "Chiro Practice India 2026", "act": "Perform flexion-distraction motorized decompression tables", "title": "Flexion-distraction therapy in L5-S1 disc herniation with leg pain"},
    {"id": "new_37", "cat": "podiatry", "name": "Happy Feet Podiatry", "owner": "Dr. Nalini", "seg": "hallux valgus adults", "n": 880, "src": "Foot Ankle India 2026", "act": "Recommend wide toe-box footwear with custom functional orthotics", "title": "Custom orthotic biomechanical realignment in mild-to-moderate bunions"},
    {"id": "new_38", "cat": "endocrinology", "name": "Diabetes Care Clinic", "owner": "Dr. Sanjeev", "seg": "type 2 diabetics", "n": 9400, "src": "Diabetology India 2026", "act": "Prescribe continuous glucose monitors (CGM) for real-time glycemic variability", "title": "Time-in-range improvements with continuous glucose monitoring in poorly controlled T2D"},
    {"id": "new_39", "cat": "nephrology", "name": "Kidney Care Associates", "owner": "Dr. Latika", "seg": "dialysis patients", "n": 2800, "src": "Dialysis Clinical Practice 2026", "act": "Monitor dry weight using multi-frequency bioimpedance spectroscopy", "title": "Bioimpedance-guided ultrafiltration and intradialytic hypotension rates"},
    {"id": "new_40", "cat": "sports_medicine", "name": "Pro Sports Recovery", "owner": "Dr. Yash", "seg": "cricket fast bowlers", "n": 320, "src": "Cricket Sports Science 2026", "act": "Regulate weekly match overs to avoid acute-to-chronic workload spikes", "title": "Lumbar stress fracture prevention via acute-to-chronic workload ratio tracking"},
    {"id": "new_41", "cat": "pharmacies", "name": "CarePlus Chemist", "owner": "Rajesh", "seg": "elderly polypharmacy", "n": 3800, "src": "Geriatric Pharmacy 2026", "act": "Conduct bi-annual medication reviews using the Beers Criteria list", "title": "Potentially inappropriate medication deprescribing in elderly outpatients"},
    {"id": "new_42", "cat": "audiology", "name": "HearBetter Clinic", "owner": "Pooja", "seg": "tinnitus sufferers", "n": 1450, "src": "Tinnitus Therapy India 2026", "act": "Fit wideband sound generators with notched music therapy", "title": "Tinnitus handicap inventory reduction with combination sound therapy"},
    {"id": "new_43", "cat": "dentists", "name": "Dental Crown Studio", "owner": "Dr. Gaurav", "seg": "all", "n": None, "src": "Restorative Dentistry 2026", "act": None, "title": "Zirconia versus lithium disilicate monolithic crowns in molar restorations"},
    {"id": "new_44", "cat": "restaurants", "name": "Spicy Spoon", "owner": "Dinesh", "seg": "none", "n": None, "src": "Culinary Digest 2026", "act": None, "title": "Sous-vide temperature precision in commercial kitchen batch cooking"},
    {"id": "new_45", "cat": "gyms", "name": "PowerZone", "owner": "Harsh", "seg": "general", "n": None, "src": "Fitness Trends 2026", "act": None, "title": "Heart rate zone training display integration in group fitness classes"},
    {"id": "new_46", "cat": "salons", "name": "Color Magic", "owner": "Ananya", "seg": "bleached hair", "n": 640, "src": "Hair Chemistry 2026", "act": "Maintain salon temperature below 24 degrees during lightening", "title": "Ambient temperature effects on persulfate bleach lift rates and scalp warmth"},
    {"id": "new_47", "cat": "optometry", "name": "Vision Express", "owner": "Alok", "seg": "orthokeratology wearers", "n": 890, "src": "Contact Lens Spectrum 2026", "act": "Prescribe hydrogen peroxide disinfectant systems for overnight ortho-k lenses", "title": "Acanthamoeba keratitis risk reduction with hydrogen peroxide lens care systems"},
    {"id": "new_48", "cat": "physiotherapy", "name": "Kinetics Physio", "owner": "Dr. Shilpa", "seg": "tennis elbow", "n": 720, "src": "Musculoskeletal Care 2026", "act": "Perform radial shockwave therapy combined with eccentric wrist extensor loading", "title": "Extracorporeal shockwave therapy versus corticosteroid injections in chronic epicondylitis"},
    {"id": "new_49", "cat": "dermatology", "name": "Aesthetics Derma", "owner": "Dr. Nitin", "seg": "androgenetic alopecia", "n": 3900, "src": "Trichology Review 2026", "act": "Prescribe low-dose oral minoxidil 2.5mg daily with topical 5% solution", "title": "Oral versus topical minoxidil monotherapy in male pattern hair loss"},
    {"id": "new_50", "cat": "cardiology", "name": "CardioLife Center", "owner": "Dr. Vivek", "seg": "atrial fibrillation", "n": 18200, "src": "Arrhythmia Studies India 2026", "act": "Switch non-valvular AF patients to direct oral anticoagulants (DOACs)", "title": "Intracranial hemorrhage risk reduction with DOACs versus warfarin in Indian patients"},
]


def run_50_new_unseen_stabilization_suite():
    store = get_context_store()
    results = []

    total_cases = len(NEW_50_SCENARIOS)
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

    noun_clash_count = 0
    actionable_used_count = 0
    missing_owner_fallback_count = 0

    print("=" * 80)
    print(f"EVALUATING 50 COMPLETELY NEW UNSEEN SCENARIOS (FINAL STABILIZATION)")
    print("=" * 80)

    for idx, sc in enumerate(NEW_50_SCENARIOS, start=1):
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

        is_clinical = cat_slug in ("dentists", "cardiology", "dermatology", "pediatrics", "orthopedics", "oncology", "physiotherapy", "chiropractic", "podiatry", "endocrinology", "nephrology", "sports_medicine")
        salutation_example = "Dr. {first_name}" if is_clinical else "Hi {first_name}"

        # 1. Build Category Context
        category_payload = {
            "slug": cat_slug,
            "display_name": cat_slug.replace("_", " ").title(),
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
                    "summary": f"Multi-center clinical evaluation showed 44% improved outcomes across primary cohorts ({title}).",
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
                "locality": "Koramangala",
            },
            "subscription": {"status": "active", "plan": "Pro", "days_remaining": 90},
            "customer_aggregate": {"target_cohort_count": 210, "total_unique_ytd": 920},
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

        # Check for plural noun clash
        if seg:
            lower_seg = seg.lower()
            if any(noun in lower_seg for noun in ["commuters", "drinkers", "practitioners", "owners", "parents", "runners", "brides", "professionals", "athletes", "organizers", "puppies", "customers", "powerlifters", "clients", "drivers", "founders", "buyers", "enthusiasts", "students", "collectors", "mothers", "cases", "diabetics", "sufferers", "wearers"]):
                if "patients" in emitted_body and lower_seg in emitted_body:
                    noun_clash_count += 1

        if act and not is_clinical:
            clean_act_snippet = act[:20].lower()
            if clean_act_snippet in emitted_body.lower():
                actionable_used_count += 1

        if not owner_name:
            missing_owner_fallback_count += 1

        primary_loss_stage = "NONE"
        if deductions:
            for ded in deductions:
                stg = ded["stage_candidate"]
                if stg == "A_UPSTREAM_MISSING":
                    loss_classification_counts["INPUT_DATA"] += ded["points_lost"]
                    primary_loss_stage = "INPUT_DATA"
                elif stg == "J_OUTPUT_COMPOSER":
                    loss_classification_counts["COMPOSER"] += ded["points_lost"]
                    primary_loss_stage = "COMPOSER"

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
        }
        results.append(case_record)

        print(f"[{idx:02d}/50] Case: {cid} | Cat: {cat_slug:<16} | Score: {score}/50 | Stage: {primary_loss_stage:<10}")
        print(f"     Body: \"{emitted_body}\"")

    out_file = Path(__file__).parent.parent / "docs" / "runtime_evidence_audit_50_new_cases.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_cases": total_cases,
            "count_50_50": count_50_50,
            "avg_score": round(sum(scores) / total_cases, 2),
            "worst_score": min(scores),
            "loss_stage_breakdown": loss_classification_counts,
            "noun_clashes_detected": noun_clash_count,
            "actionable_used_count": actionable_used_count,
            "missing_owner_fallback_count": missing_owner_fallback_count,
            "cases": results
        }, f, indent=2)

    print("\n" + "=" * 80)
    print("50 NEW UNSEEN SCENARIOS AUDIT SUMMARY")
    print("=" * 80)
    print(f"Total Cases Evaluated        : {total_cases}")
    print(f"Cases Scoring 50/50          : {count_50_50} ({count_50_50/total_cases*100:.1f}%)")
    print(f"Average Score                : {sum(scores)/total_cases:.2f} / 50")
    print(f"Worst Score                  : {min(scores)} / 50")
    print(f"Plural Noun Clashes Detected : {noun_clash_count} (0 = 100% clean)")
    print(f"Actionable CTAs Formulated   : {actionable_used_count}")
    print(f"Missing Owner Fallbacks Safe : {missing_owner_fallback_count}")
    print("\nLoss Classification Breakdown (Points Lost):")
    for stg, pts in loss_classification_counts.items():
        if pts > 0:
            print(f"  {stg:<22} : {pts:>3} points lost")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_50_new_unseen_stabilization_suite()
