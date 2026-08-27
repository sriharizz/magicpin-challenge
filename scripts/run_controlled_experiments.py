import os
import sys
import json
import time
import urllib.request
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\projects\magicpin')
sys.path.insert(0, r'c:\projects\magicpin\magicpin-ai-challenge')

from judge_simulator import LLMScorer, LLMProvider, ScoreResult, DATASET_DIR
from app.engine.composer import (
    _extract_lead_hook,
    _synthesize_finding,
    _clean_taboo_terms,
    _validate_taboo_words,
    _is_expired,
    _has_opted_out,
)
from app.engine.salutation import resolve_salutation as baseline_resolve_salutation
from app.models.interaction import TickAction

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

class GroqExperimentProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = 'openai/gpt-oss-120b'):
        self.api_key = api_key
        self.model = model

    def name(self) -> str:
        return f'Groq ({self.model})'

    def complete(self, prompt: str, system: str = None) -> str:
        messages = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.append({'role': 'user', 'content': prompt})

        payload = json.dumps({
            'model': self.model,
            'messages': messages,
            'temperature': 0.2,
            'max_tokens': 1200
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=payload,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'magicpin-experiment-runner/1.0'
            }
        )
        for attempt in range(4):
            try:
                resp = urllib.request.urlopen(req, timeout=25)
                data = json.loads(resp.read().decode('utf-8'))
                return data['choices'][0]['message']['content']
            except Exception as e:
                time.sleep(1.5 * (attempt + 1))
                if attempt == 3:
                    raise e

# --- EXPERIMENTAL SALUTATION ---
def exp_resolve_salutation(category: Dict[str, Any], merchant: Dict[str, Any]) -> str:
    """
    Experimental salutation resolution:
    1. owner_first_name if present
    2. business identity (name) if owner missing
    3. locality + "Team" if business name missing
    4. neutral fallback only if all missing
    """
    voice = category.get("voice", {}) if isinstance(category, dict) else {}
    salutation_examples = voice.get("salutation_examples", []) if isinstance(voice, dict) else []

    identity = merchant.get("identity", {}) if isinstance(merchant, dict) else {}
    owner_first_name = identity.get("owner_first_name")
    biz_name = identity.get("name")
    locality = identity.get("locality")

    clean_name = ""
    if owner_first_name:
        candidate = str(owner_first_name).strip()
        if candidate.lower() not in ("none", "null", ""):
            clean_name = candidate

    clean_biz = ""
    if biz_name:
        candidate_biz = str(biz_name).strip()
        if candidate_biz.lower() not in ("none", "null", ""):
            clean_biz = candidate_biz

    clean_loc = ""
    if locality:
        candidate_loc = str(locality).strip()
        if candidate_loc.lower() not in ("none", "null", ""):
            clean_loc = candidate_loc

    is_doctor_pattern = any("dr." in str(ex).lower() or "doc" in str(ex).lower() for ex in salutation_examples)

    if is_doctor_pattern:
        if clean_name:
            lower = clean_name.lower()
            if lower.startswith("dr.") or lower.startswith("dr "):
                return f"Dr. {clean_name[3:].strip()}"
            return f"Dr. {clean_name}"
        if clean_biz:
            return f"Hi {clean_biz} team"
        if clean_loc:
            return f"Hi {clean_loc} clinic team"
        return "Doctor"

    if clean_name:
        return f"Hi {clean_name}"
    if clean_biz:
        return f"Hi {clean_biz} team"
    if clean_loc:
        return f"Hi {clean_loc} team"

    return "Hi there"

# --- EXPERIMENTAL CTA ---
def exp_resolve_topic_cta(digest_item: Dict[str, Any], category: Dict[str, Any]) -> str:
    """
    Experimental CTA with tailored binary confirmation:
    """
    kind = str(digest_item.get("kind", "")).lower()
    cat_slug = str(category.get("slug", "")).lower()
    patient_content_lib = category.get("patient_content_library", [])

    if kind in ("compliance", "regulation"):
        return "Worth a look. Want me to pull the compliance checklist? Reply YES to send."
    elif kind in ("tech", "equipment"):
        return "Worth a look (2-min abstract). Want me to pull the comparison details? Reply YES."
    elif kind in ("cde", "webinar"):
        return "Worth a look. Want me to pull the session credits info? Reply YES."
    elif kind in ("trend", "seasonal"):
        return "Worth a look. Want me to pull the local demand breakdown for your area? Reply YES."
    elif patient_content_lib and cat_slug in ("dentists", "salons", "clinics", "pharmacies"):
        return "Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp you can share? Reply YES."
    else:
        return "Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES."

# --- EXPERIMENTAL COMPOSER ---
def compose_variant(
    category: Dict[str, Any],
    merchant: Dict[str, Any],
    trigger: Dict[str, Any],
    now: str,
    variant: str = "baseline" # "baseline", "identity_only", "cta_only", "both"
) -> Optional[TickAction]:
    if trigger.get("scope") != "merchant" or trigger.get("kind") != "research_digest":
        return None
    if _is_expired(now, trigger.get("expires_at")):
        return None
    trg_cat = trigger.get("payload", {}).get("category")
    merchant_cat = merchant.get("category_slug")
    if trg_cat and merchant_cat and trg_cat.lower() != merchant_cat.lower():
        return None
    sub = merchant.get("subscription", {})
    if str(sub.get("status", "")).lower() in ("expired", "cancelled", "churned") and sub.get("days_remaining", 0) <= 0:
        return None
    if _has_opted_out(merchant):
        return None

    top_item_id = trigger.get("payload", {}).get("top_item_id")
    digest_items = category.get("digest", []) or category.get("digest_items", [])
    matched_item = None
    if top_item_id:
        for item in digest_items:
            if isinstance(item, dict) and item.get("id") == top_item_id:
                matched_item = item
                break
    if not matched_item and digest_items:
        matched_item = digest_items[0]
    if not matched_item:
        return None

    source = str(matched_item.get("source", "")).strip()
    title = str(matched_item.get("title", "")).strip()
    trial_n = matched_item.get("trial_n")
    if isinstance(trial_n, str) and trial_n.isdigit():
        trial_n = int(trial_n)
    patient_segment = str(matched_item.get("patient_segment", "")).strip()
    summary = str(matched_item.get("summary", "")).strip()

    # Salutation selection
    if variant in ("identity_only", "both"):
        salutation = exp_resolve_salutation(category, merchant)
    else:
        salutation = baseline_resolve_salutation(category, merchant)

    hook = _extract_lead_hook(source)

    signals = merchant.get("signals", [])
    customer_agg = merchant.get("customer_aggregate", {})
    high_risk_count = customer_agg.get("high_risk_adult_count")

    cohort_phrase = ""
    if patient_segment == "high_risk_adults" and ("high_risk_adult_cohort" in signals or high_risk_count):
        cohort_phrase = "One item relevant to your high-risk adult patients — "
    elif patient_segment and patient_segment.lower() not in ("all", "general", "none"):
        clean_seg = patient_segment.replace("_", " ")
        if "patient" not in clean_seg and "client" not in clean_seg:
            cohort_phrase = f"One item relevant to {clean_seg} patients — "
        else:
            cohort_phrase = f"One item relevant to {clean_seg} — "
    else:
        cohort_phrase = "One item relevant to your practice — "

    fact_finding = _synthesize_finding(summary=summary, title=title, trial_n=trial_n)
    if not fact_finding:
        return None

    # CTA selection
    if variant in ("cta_only", "both"):
        cta_text = exp_resolve_topic_cta(matched_item, category)
    else:
        from app.engine.composer import _resolve_topic_cta as baseline_resolve_cta
        cta_text = baseline_resolve_cta(matched_item, category)

    citation_footer = f" — {source}" if source else ""
    raw_body = f"{salutation}, {hook} {cohort_phrase}{fact_finding} {cta_text}{citation_footer}"

    voice = category.get("voice", {})
    taboo_terms = _clean_taboo_terms(voice.get("vocab_taboo", []))
    body_text = _validate_taboo_words(raw_body, taboo_terms)

    merchant_id = merchant.get("merchant_id", "m_unknown")
    trigger_id = trigger.get("id", "trg_unknown")

    return TickAction(
        conversation_id=f"conv_{merchant_id}_{trigger_id}",
        merchant_id=merchant_id,
        customer_id=None,
        send_as="vera",
        trigger_id=trigger_id,
        template_name=f"vera_research_digest_{variant}",
        template_params=[salutation, f"{hook} {cohort_phrase}{fact_finding}", cta_text],
        body=body_text,
        cta="open_ended",
        suppression_key=trigger.get("suppression_key") or f"research:{merchant_id}",
        rationale=f"Controlled experiment variant {variant}",
    )

def run_experiments():
    print("=======================================================================")
    print("VERA CONTROLLED QUALITY EXPERIMENT: A (Baseline), B (Identity), C (CTA), D (Both)")
    print("=======================================================================")

    cases_path = Path(r"c:\projects\magicpin\tests\quality_cases.json")
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    # Filter to cases that produce proactive actions
    proactive_cases = []
    for c in cases:
        cat = c["category_context"]
        merch = c["merchant_context"]
        trg = c["trigger_context"]
        act = compose_variant(cat, merch, trg, "2026-04-26T10:00:00Z", "baseline")
        if act:
            proactive_cases.append(c)

    print(f"Total Quality Cases: {len(cases)}")
    print(f"Active Proactive Evaluated Cases: {len(proactive_cases)}")

    # We evaluate 25 representative cases across all categories and densities across all 4 variants
    eval_set = proactive_cases[:25]
    
    provider = GroqExperimentProvider(api_key=GROQ_API_KEY)
    class DatasetStub:
        pass
    ds = DatasetStub()
    ds.categories = {}
    ds.merchants = {}
    ds.customers = {}
    ds.triggers = {}
    scorer = LLMScorer(provider, ds)

    variants = ["baseline", "identity_only", "cta_only", "both"]
    results = {v: [] for v in variants}

    for v in variants:
        print(f"\n---> Scoring Variant: [{v.upper()}] on {len(eval_set)} cases via Groq 120B...")
        for idx, c in enumerate(eval_set, 1):
            cat = c["category_context"]
            merch = c["merchant_context"]
            trg = c["trigger_context"]
            
            act = compose_variant(cat, merch, trg, "2026-04-26T10:00:00Z", v)
            score = scorer.score(act.dict(), cat, merch, trg, None)
            
            rec = {
                "case_id": c["case_id"],
                "category": c["category"],
                "context_density": c["context_density"],
                "merchant_id": merch["merchant_id"],
                "body": act.body,
                "score": score
            }
            results[v].append(rec)
            print(f"  [{idx}/{len(eval_set)}] Case {c['case_id']} ({c['category']}) -> Score: {score.total}/50 | Spec: {score.specificity}, Cat: {score.category_fit}, Merch: {score.merchant_fit}, Dec: {score.decision_quality}, Eng: {score.engagement_compulsion}")
            time.sleep(0.35)

    # Statistical Summary per Variant
    summary = {}
    for v in variants:
        totals = [r["score"].total for r in results[v]]
        specs = [r["score"].specificity for r in results[v]]
        cats = [r["score"].category_fit for r in results[v]]
        merchs = [r["score"].merchant_fit for r in results[v]]
        decs = [r["score"].decision_quality for r in results[v]]
        engs = [r["score"].engagement_compulsion for r in results[v]]
        penalties = [r["score"].penalties for r in results[v]]

        summary[v] = {
            "mean": float(np.mean(totals)),
            "median": float(np.median(totals)),
            "specificity": float(np.mean(specs)),
            "category_fit": float(np.mean(cats)),
            "merchant_fit": float(np.mean(merchs)),
            "decision_quality": float(np.mean(decs)),
            "engagement": float(np.mean(engs)),
            "penalties": float(sum(penalties)),
            "penalty_rate": float(sum(1 for p in penalties if p > 0) / len(penalties))
        }

    # Category Breakdowns
    cat_summary = {v: {} for v in variants}
    for v in variants:
        by_cat = {}
        for r in results[v]:
            by_cat.setdefault(r["category"], []).append(r["score"].total)
        for cat, scs in by_cat.items():
            cat_summary[v][cat] = float(np.mean(scs))

    # Density Breakdowns
    density_summary = {v: {} for v in variants}
    for v in variants:
        by_dens = {}
        for r in results[v]:
            by_dens.setdefault(r["context_density"], []).append(r["score"].total)
        for dens, scs in by_dens.items():
            density_summary[v][dens] = float(np.mean(scs))

    # Regressions Analysis (Comparing each variant against baseline)
    regressions = []
    for idx in range(len(eval_set)):
        base_rec = results["baseline"][idx]
        base_tot = base_rec["score"].total
        
        for v in ["identity_only", "cta_only", "both"]:
            var_rec = results[v][idx]
            var_tot = var_rec["score"].total
            
            if var_tot < base_tot:
                diff = base_tot - var_tot
                regressions.append({
                    "case_id": base_rec["case_id"],
                    "variant": v,
                    "category": base_rec["category"],
                    "density": base_rec["context_density"],
                    "baseline_score": base_tot,
                    "variant_score": var_tot,
                    "diff": diff,
                    "baseline_body": base_rec["body"],
                    "variant_body": var_rec["body"],
                    "baseline_reasons": f"Spec:{base_rec['score'].specificity} Cat:{base_rec['score'].category_fit} Merch:{base_rec['score'].merchant_fit} Dec:{base_rec['score'].decision_quality} Eng:{base_rec['score'].engagement_compulsion}",
                    "variant_reasons": f"Spec:{var_rec['score'].specificity} Cat:{var_rec['score'].category_fit} Merch:{var_rec['score'].merchant_fit} Dec:{var_rec['score'].decision_quality} Eng:{var_rec['score'].engagement_compulsion}",
                    "hint": var_rec["score"].hint
                })

    regressions_sorted = sorted(regressions, key=lambda x: x["diff"], reverse=True)

    # Write regressions document
    with open(r"c:\projects\magicpin\docs\quality_experiment_regressions.md", "w", encoding="utf-8") as f:
        f.write("# Vera Quality Experiment Regression Analysis\n\n")
        f.write(f"Total Evaluated Cases: {len(eval_set)} across 4 experimental variants.\n")
        f.write(f"Total Detected Regressions vs Baseline: {len(regressions_sorted)}\n\n")
        f.write("## Top Regressions (Score Decreases vs Baseline)\n\n")
        if not regressions_sorted:
            f.write("Zero regressions observed! All experimental variants achieved equal or strictly superior scores compared to baseline.\n")
        else:
            for r_idx, reg in enumerate(regressions_sorted[:20], 1):
                f.write(f"### {r_idx}. Case `{reg['case_id']}` ({reg['category']}, {reg['density']}) — Variant `{reg['variant']}`\n")
                f.write(f"- **Score Impact**: {reg['baseline_score']} -> {reg['variant_score']} (Drop: -{reg['diff']} pts)\n")
                f.write(f"- **Baseline Body**: `{reg['baseline_body']}`\n")
                f.write(f"- **Variant Body**: `{reg['variant_body']}`\n")
                f.write(f"- **Baseline Breakdown**: {reg['baseline_reasons']}\n")
                f.write(f"- **Variant Breakdown**: {reg['variant_reasons']}\n")
                f.write(f"- **Judge Hint**: {reg['hint']}\n\n")

    print("\n=======================================================================")
    print("EXPERIMENT COMPARATIVE RESULTS TABLE")
    print("=======================================================================")
    print(f"{'Metric':<22} | {'BASELINE':<10} | {'IDENTITY':<10} | {'CTA':<10} | {'BOTH':<10}")
    print("-" * 72)
    print(f"{'Mean Score':<22} | {summary['baseline']['mean']:<10.2f} | {summary['identity_only']['mean']:<10.2f} | {summary['cta_only']['mean']:<10.2f} | {summary['both']['mean']:<10.2f}")
    print(f"{'Median Score':<22} | {summary['baseline']['median']:<10.2f} | {summary['identity_only']['median']:<10.2f} | {summary['cta_only']['median']:<10.2f} | {summary['both']['median']:<10.2f}")
    print(f"{'Specificity (avg)':<22} | {summary['baseline']['specificity']:<10.2f} | {summary['identity_only']['specificity']:<10.2f} | {summary['cta_only']['specificity']:<10.2f} | {summary['both']['specificity']:<10.2f}")
    print(f"{'Category Fit (avg)':<22} | {summary['baseline']['category_fit']:<10.2f} | {summary['identity_only']['category_fit']:<10.2f} | {summary['cta_only']['category_fit']:<10.2f} | {summary['both']['category_fit']:<10.2f}")
    print(f"{'Merchant Fit (avg)':<22} | {summary['baseline']['merchant_fit']:<10.2f} | {summary['identity_only']['merchant_fit']:<10.2f} | {summary['cta_only']['merchant_fit']:<10.2f} | {summary['both']['merchant_fit']:<10.2f}")
    print(f"{'Decision Quality (avg)':<22} | {summary['baseline']['decision_quality']:<10.2f} | {summary['identity_only']['decision_quality']:<10.2f} | {summary['cta_only']['decision_quality']:<10.2f} | {summary['both']['decision_quality']:<10.2f}")
    print(f"{'Engagement (avg)':<22} | {summary['baseline']['engagement']:<10.2f} | {summary['identity_only']['engagement']:<10.2f} | {summary['cta_only']['engagement']:<10.2f} | {summary['both']['engagement']:<10.2f}")
    print(f"{'Penalty Rate':<22} | {summary['baseline']['penalty_rate']*100:<9.1f}% | {summary['identity_only']['penalty_rate']*100:<9.1f}% | {summary['cta_only']['penalty_rate']*100:<9.1f}% | {summary['both']['penalty_rate']*100:<9.1f}%")
    print("=======================================================================")

    # Write complete experiment results to json
    exp_out = {
        "summary": summary,
        "category_summary": cat_summary,
        "density_summary": density_summary,
        "total_regressions": len(regressions_sorted),
        "regressions": regressions_sorted
    }
    with open(r"c:\projects\magicpin\tests\experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(exp_out, f, indent=2)

if __name__ == "__main__":
    run_experiments()
