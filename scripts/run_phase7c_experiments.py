import os
import sys
import json
import time
import urllib.request
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
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

class GroqPhase7CProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = 'openai/gpt-oss-20b'):
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
                'User-Agent': 'magicpin-phase7c-runner/1.0'
            }
        )
        for attempt in range(6):
            try:
                req = urllib.request.Request(
                    'https://api.groq.com/openai/v1/chat/completions',
                    data=payload,
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                        'User-Agent': 'magicpin-phase7c-runner/1.0'
                    }
                )
                resp = urllib.request.urlopen(req, timeout=30)
                data = json.loads(resp.read().decode('utf-8'))
                return data['choices'][0]['message']['content']
            except Exception as e:
                time.sleep(3.0 * (attempt + 1))
                if attempt == 5:
                    raise e

# --- 1. CONDITIONAL IDENTITY RESOLVER ---
CLINICAL_CATEGORIES = {"dentists", "physiotherapy", "optometry", "clinics", "hospitals"}

def resolve_conditional_identity(category: Dict[str, Any], merchant: Dict[str, Any]) -> str:
    cat_slug = str(category.get("slug", "")).lower()
    voice = category.get("voice", {}) if isinstance(category, dict) else {}
    salutation_examples = voice.get("salutation_examples", []) if isinstance(voice, dict) else []

    identity = merchant.get("identity", {}) if isinstance(merchant, dict) else {}
    owner_first_name = identity.get("owner_first_name")
    biz_name = identity.get("name")
    locality = identity.get("locality")

    clean_owner = ""
    if owner_first_name:
        candidate = str(owner_first_name).strip()
        if candidate.lower() not in ("none", "null", ""):
            clean_owner = candidate

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

    is_clinical = (cat_slug in CLINICAL_CATEGORIES) or any("dr." in str(ex).lower() or "doc" in str(ex).lower() for ex in salutation_examples)

    if is_clinical:
        if clean_owner:
            lower = clean_owner.lower()
            if lower.startswith("dr.") or lower.startswith("dr "):
                return f"Dr. {clean_owner[3:].strip()}"
            return f"Dr. {clean_owner}"
        # Doctor vertical fallback: use "Doctor" or "Doc" (never dilute clinical authority)
        for ex in salutation_examples:
            ex_str = str(ex).strip()
            if "{" not in ex_str and ex_str:
                return ex_str
        return "Doctor"

    # Commercial Verticals (Salons, Pharmacies, Gyms, Restaurants, Pet Care)
    if clean_owner:
        return f"Hi {clean_owner}"
    if clean_biz:
        return f"Hi {clean_biz} team"
    if clean_loc:
        return f"Hi {clean_loc} team"

    return "Hi there"

# --- 2. CONTEXT-AWARE CTA RESOLVER ---
def resolve_context_aware_cta(digest_item: Dict[str, Any], category: Dict[str, Any], merchant: Dict[str, Any]) -> str:
    kind = str(digest_item.get("kind", "")).lower()
    cat_slug = str(category.get("slug", "")).lower()
    patient_content_lib = category.get("patient_content_library", [])
    identity = merchant.get("identity", {}) if isinstance(merchant, dict) else {}
    locality = identity.get("locality")

    if kind in ("compliance", "regulation"):
        return "Worth a look. Want me to pull the compliance checklist? Reply YES."
    elif kind in ("tech", "equipment"):
        return "Worth a look (2-min abstract). Want me to pull the workflow and comparison details? Reply YES."
    elif kind in ("cde", "webinar"):
        return "Worth a look. Want me to pull the session credits info? Reply YES."
    elif kind in ("trend", "seasonal"):
        if locality:
            return f"Worth a look. Want me to pull the {locality} demand breakdown for your area? Reply YES."
        return "Worth a look. Want me to pull the local demand breakdown for your area? Reply YES."
    elif patient_content_lib and cat_slug in ("dentists", "salons", "clinics", "pharmacies"):
        return "Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp you can share? Reply YES."
    else:
        return "Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES."

# --- 3. SPECIFICITY ENRICHED COMPOSER ---
def compose_phase7c_variant(
    category: Dict[str, Any],
    merchant: Dict[str, Any],
    trigger: Dict[str, Any],
    now: str,
    variant: str = "baseline" # "baseline", "conditional_identity", "context_cta", "specificity_enrichment", "all_three"
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
    if variant in ("conditional_identity", "all_three"):
        salutation = resolve_conditional_identity(category, merchant)
    else:
        salutation = baseline_resolve_salutation(category, merchant)

    hook = _extract_lead_hook(source)

    signals = merchant.get("signals", [])
    customer_agg = merchant.get("customer_aggregate", {})
    high_risk_count = customer_agg.get("high_risk_adult_count")

    # Specificity cohort anchor selection
    if variant in ("specificity_enrichment", "all_three"):
        if patient_segment == "high_risk_adults" and high_risk_count and isinstance(high_risk_count, int) and high_risk_count > 0:
            cohort_phrase = f"One item relevant to your {high_risk_count} high-risk adult patients — "
        elif patient_segment == "high_risk_adults" and "high_risk_adult_cohort" in signals:
            cohort_phrase = "One item relevant to your high-risk adult patients — "
        elif patient_segment and patient_segment.lower() not in ("all", "general", "none"):
            clean_seg = patient_segment.replace("_", " ")
            if "patient" not in clean_seg and "client" not in clean_seg:
                cohort_phrase = f"One item relevant to {clean_seg} patients — "
            else:
                cohort_phrase = f"One item relevant to {clean_seg} — "
        else:
            cohort_phrase = "One item relevant to your practice — "
    else:
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
    if variant in ("context_cta", "all_three"):
        cta_text = resolve_context_aware_cta(matched_item, category, merchant)
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
        rationale=f"Phase 7C targeted variant {variant}",
    )

def run_phase7c_benchmark():
    print("=======================================================================")
    print("VERA PHASE 7C: TARGETED QUALITY OPTIMIZATION BENCHMARK")
    print("=======================================================================")

    cases_path = Path(r"c:\projects\magicpin\tests\quality_cases.json")
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    proactive_cases = []
    for c in cases:
        cat = c["category_context"]
        merch = c["merchant_context"]
        trg = c["trigger_context"]
        act = compose_phase7c_variant(cat, merch, trg, "2026-04-26T10:00:00Z", "baseline")
        if act:
            proactive_cases.append(c)

    eval_set = proactive_cases[:25]
    print(f"Total Quality Cases: {len(cases)} | Evaluated Active Cases: {len(eval_set)}")

    provider = GroqPhase7CProvider(api_key=GROQ_API_KEY)
    class DatasetStub:
        pass
    ds = DatasetStub()
    ds.categories = {}
    ds.merchants = {}
    ds.customers = {}
    ds.triggers = {}
    scorer = LLMScorer(provider, ds)

    variants = [
        "baseline",
        "conditional_identity",
        "context_cta",
        "specificity_enrichment",
        "all_three"
    ]
    results = {v: [] for v in variants}

    for v in variants:
        print(f"\n---> Scoring Phase 7C Variant: [{v.upper()}] across {len(eval_set)} cases...")
        for idx, c in enumerate(eval_set, 1):
            cat = c["category_context"]
            merch = c["merchant_context"]
            trg = c["trigger_context"]

            act = compose_phase7c_variant(cat, merch, trg, "2026-04-26T10:00:00Z", v)
            score = scorer.score(act.model_dump(), cat, merch, trg, None)

            rec = {
                "case_id": c["case_id"],
                "category": c["category"],
                "context_density": c["context_density"],
                "merchant_id": merch["merchant_id"],
                "body": act.body,
                "score": score
            }
            results[v].append(rec)
            print(f"  [{idx}/{len(eval_set)}] {c['case_id']} ({c['category']}, {c['context_density']}) -> Total: {score.total}/50 | Spec: {score.specificity}, Cat: {score.category_fit}, Merch: {score.merchant_fit}, Dec: {score.decision_quality}, Eng: {score.engagement_compulsion}")
            time.sleep(1.0)

    # Statistical Summaries
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
            "min": int(np.min(totals)),
            "max": int(np.max(totals)),
            "specificity": float(np.mean(specs)),
            "category_fit": float(np.mean(cats)),
            "merchant_fit": float(np.mean(merchs)),
            "decision_quality": float(np.mean(decs)),
            "engagement": float(np.mean(engs)),
            "penalties": float(sum(penalties)),
            "penalty_rate": float(sum(1 for p in penalties if p > 0) / len(penalties))
        }

    # Category Summaries
    cat_summary = {v: {} for v in variants}
    for v in variants:
        by_cat = {}
        for r in results[v]:
            by_cat.setdefault(r["category"], []).append(r["score"].total)
        for cat, scs in by_cat.items():
            cat_summary[v][cat] = float(np.mean(scs))

    # Density Summaries
    density_summary = {v: {} for v in variants}
    for v in variants:
        by_dens = {}
        for r in results[v]:
            by_dens.setdefault(r["context_density"], []).append(r["score"].total)
        for dens, scs in by_dens.items():
            density_summary[v][dens] = float(np.mean(scs))

    # Regressions Analysis
    regressions = []
    for idx in range(len(eval_set)):
        base_rec = results["baseline"][idx]
        base_tot = base_rec["score"].total

        for v in ["conditional_identity", "context_cta", "specificity_enrichment", "all_three"]:
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
                    "baseline_breakdown": f"Spec:{base_rec['score'].specificity} Cat:{base_rec['score'].category_fit} Merch:{base_rec['score'].merchant_fit} Dec:{base_rec['score'].decision_quality} Eng:{base_rec['score'].engagement_compulsion}",
                    "variant_breakdown": f"Spec:{var_rec['score'].specificity} Cat:{var_rec['score'].category_fit} Merch:{var_rec['score'].merchant_fit} Dec:{var_rec['score'].decision_quality} Eng:{var_rec['score'].engagement_compulsion}",
                    "hint": var_rec["score"].hint
                })

    regressions_sorted = sorted(regressions, key=lambda x: x["diff"], reverse=True)

    # Write documentation report
    doc_path = Path(r"c:\projects\magicpin\docs\phase7c_quality_optimization.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("# Vera Phase 7C Targeted Quality Optimization Report\n\n")
        f.write("## 1. Comparative Executive Results\n\n")
        f.write("| Metric | BASELINE | CONDITIONAL IDENTITY | CONTEXT CTA | SPECIFICITY ENRICHMENT | ALL THREE |\n")
        f.write("|:---|:---:|:---:|:---:|:---:|:---:|\n")
        f.write(f"| **Mean Score** | {summary['baseline']['mean']:.2f} | {summary['conditional_identity']['mean']:.2f} | {summary['context_cta']['mean']:.2f} | {summary['specificity_enrichment']['mean']:.2f} | **{summary['all_three']['mean']:.2f}** |\n")
        f.write(f"| **Median Score** | {summary['baseline']['median']:.2f} | {summary['conditional_identity']['median']:.2f} | {summary['context_cta']['median']:.2f} | {summary['specificity_enrichment']['median']:.2f} | **{summary['all_three']['median']:.2f}** |\n")
        f.write(f"| **Min / Max** | {summary['baseline']['min']}/{summary['baseline']['max']} | {summary['conditional_identity']['min']}/{summary['conditional_identity']['max']} | {summary['context_cta']['min']}/{summary['context_cta']['max']} | {summary['specificity_enrichment']['min']}/{summary['specificity_enrichment']['max']} | **{summary['all_three']['min']}/{summary['all_three']['max']}** |\n")
        f.write(f"| **Specificity (avg)** | {summary['baseline']['specificity']:.2f} | {summary['conditional_identity']['specificity']:.2f} | {summary['context_cta']['specificity']:.2f} | {summary['specificity_enrichment']['specificity']:.2f} | **{summary['all_three']['specificity']:.2f}** |\n")
        f.write(f"| **Category Fit (avg)** | {summary['baseline']['category_fit']:.2f} | {summary['conditional_identity']['category_fit']:.2f} | {summary['context_cta']['category_fit']:.2f} | {summary['specificity_enrichment']['category_fit']:.2f} | **{summary['all_three']['category_fit']:.2f}** |\n")
        f.write(f"| **Merchant Fit (avg)** | {summary['baseline']['merchant_fit']:.2f} | {summary['conditional_identity']['merchant_fit']:.2f} | {summary['context_cta']['merchant_fit']:.2f} | {summary['specificity_enrichment']['merchant_fit']:.2f} | **{summary['all_three']['merchant_fit']:.2f}** |\n")
        f.write(f"| **Decision Quality (avg)** | {summary['baseline']['decision_quality']:.2f} | {summary['conditional_identity']['decision_quality']:.2f} | {summary['context_cta']['decision_quality']:.2f} | {summary['specificity_enrichment']['decision_quality']:.2f} | **{summary['all_three']['decision_quality']:.2f}** |\n")
        f.write(f"| **Engagement (avg)** | {summary['baseline']['engagement']:.2f} | {summary['conditional_identity']['engagement']:.2f} | {summary['context_cta']['engagement']:.2f} | {summary['specificity_enrichment']['engagement']:.2f} | **{summary['all_three']['engagement']:.2f}** |\n")
        f.write(f"| **Penalty Rate** | {summary['baseline']['penalty_rate']*100:.1f}% | {summary['conditional_identity']['penalty_rate']*100:.1f}% | {summary['context_cta']['penalty_rate']*100:.1f}% | {summary['specificity_enrichment']['penalty_rate']*100:.1f}% | **{summary['all_three']['penalty_rate']*100:.1f}%** |\n\n")

        f.write("## 2. Category Performance Comparison\n\n")
        f.write("| Category | BASELINE | CONDITIONAL IDENTITY | CONTEXT CTA | SPECIFICITY ENRICHMENT | ALL THREE |\n")
        f.write("|:---|:---:|:---:|:---:|:---:|:---:|\n")
        all_cats = sorted(set(cat_summary['baseline'].keys()))
        for cat in all_cats:
            f.write(f"| **{cat.title()}** | {cat_summary['baseline'].get(cat, 0):.2f} | {cat_summary['conditional_identity'].get(cat, 0):.2f} | {cat_summary['context_cta'].get(cat, 0):.2f} | {cat_summary['specificity_enrichment'].get(cat, 0):.2f} | **{cat_summary['all_three'].get(cat, 0):.2f}** |\n")
        f.write("\n")

        f.write("## 3. Context Density Performance Comparison\n\n")
        f.write("| Context Density | BASELINE | CONDITIONAL IDENTITY | CONTEXT CTA | SPECIFICITY ENRICHMENT | ALL THREE |\n")
        f.write("|:---|:---:|:---:|:---:|:---:|:---:|\n")
        all_dens = sorted(set(density_summary['baseline'].keys()))
        for dens in all_dens:
            f.write(f"| **{dens.title()}** | {density_summary['baseline'].get(dens, 0):.2f} | {density_summary['conditional_identity'].get(dens, 0):.2f} | {density_summary['context_cta'].get(dens, 0):.2f} | {density_summary['specificity_enrichment'].get(dens, 0):.2f} | **{density_summary['all_three'].get(dens, 0):.2f}** |\n")
        f.write("\n")

        f.write("## 4. Regression Analysis\n\n")
        f.write(f"Total Detected Regressions vs Baseline: {len(regressions_sorted)}\n\n")
        for r_idx, reg in enumerate(regressions_sorted[:20], 1):
            f.write(f"### {r_idx}. Case `{reg['case_id']}` ({reg['category']}, {reg['density']}) — Variant `{reg['variant']}`\n")
            f.write(f"- **Score Impact**: {reg['baseline_score']} -> {reg['variant_score']} (-{reg['diff']} pts)\n")
            f.write(f"- **Baseline Body**: `{reg['baseline_body']}`\n")
            f.write(f"- **Variant Body**: `{reg['variant_body']}`\n")
            f.write(f"- **Baseline Breakdown**: {reg['baseline_breakdown']}\n")
            f.write(f"- **Variant Breakdown**: {reg['variant_breakdown']}\n")
            f.write(f"- **Judge Hint**: {reg['hint']}\n\n")

    print("\n=======================================================================")
    print("PHASE 7C FINAL COMPARATIVE RESULTS")
    print("=======================================================================")
    print(f"{'Metric':<24} | {'BASELINE':<10} | {'COND_IDENT':<10} | {'CTX_CTA':<10} | {'SPEC_ENRICH':<11} | {'ALL_THREE':<10}")
    print("-" * 84)
    print(f"{'Mean Score':<24} | {summary['baseline']['mean']:<10.2f} | {summary['conditional_identity']['mean']:<10.2f} | {summary['context_cta']['mean']:<10.2f} | {summary['specificity_enrichment']['mean']:<11.2f} | {summary['all_three']['mean']:<10.2f}")
    print(f"{'Median Score':<24} | {summary['baseline']['median']:<10.2f} | {summary['conditional_identity']['median']:<10.2f} | {summary['context_cta']['median']:<10.2f} | {summary['specificity_enrichment']['median']:<11.2f} | {summary['all_three']['median']:<10.2f}")
    print(f"{'Specificity (avg)':<24} | {summary['baseline']['specificity']:<10.2f} | {summary['conditional_identity']['specificity']:<10.2f} | {summary['context_cta']['specificity']:<10.2f} | {summary['specificity_enrichment']['specificity']:<11.2f} | {summary['all_three']['specificity']:<10.2f}")
    print(f"{'Category Fit (avg)':<24} | {summary['baseline']['category_fit']:<10.2f} | {summary['conditional_identity']['category_fit']:<10.2f} | {summary['context_cta']['category_fit']:<10.2f} | {summary['specificity_enrichment']['category_fit']:<11.2f} | {summary['all_three']['category_fit']:<10.2f}")
    print(f"{'Merchant Fit (avg)':<24} | {summary['baseline']['merchant_fit']:<10.2f} | {summary['conditional_identity']['merchant_fit']:<10.2f} | {summary['context_cta']['merchant_fit']:<10.2f} | {summary['specificity_enrichment']['merchant_fit']:<11.2f} | {summary['all_three']['merchant_fit']:<10.2f}")
    print(f"{'Decision Quality (avg)':<24} | {summary['baseline']['decision_quality']:<10.2f} | {summary['conditional_identity']['decision_quality']:<10.2f} | {summary['context_cta']['decision_quality']:<10.2f} | {summary['specificity_enrichment']['decision_quality']:<11.2f} | {summary['all_three']['decision_quality']:<10.2f}")
    print(f"{'Engagement (avg)':<24} | {summary['baseline']['engagement']:<10.2f} | {summary['conditional_identity']['engagement']:<10.2f} | {summary['context_cta']['engagement']:<10.2f} | {summary['specificity_enrichment']['engagement']:<11.2f} | {summary['all_three']['engagement']:<10.2f}")
    print(f"{'Penalty Rate':<24} | {summary['baseline']['penalty_rate']*100:<9.1f}% | {summary['conditional_identity']['penalty_rate']*100:<9.1f}% | {summary['context_cta']['penalty_rate']*100:<9.1f}% | {summary['specificity_enrichment']['penalty_rate']*100:<10.1f}% | {summary['all_three']['penalty_rate']*100:<9.1f}%")
    print("=======================================================================")

if __name__ == "__main__":
    run_phase7c_benchmark()
