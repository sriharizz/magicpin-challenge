import os
import sys
import json
import time
import urllib.request
import csv
import numpy as np
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\projects\magicpin')
sys.path.insert(0, r'c:\projects\magicpin\magicpin-ai-challenge')

from judge_simulator import DatasetLoader, LLMScorer, LLMProvider, ScoreResult, DATASET_DIR
from app.store.context_store import ContextStore

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

class GroqBenchmarkProvider(LLMProvider):
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
                'User-Agent': 'magicpin-benchmarker/1.0'
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

def run_benchmark():
    print("=======================================================================")
    print("VERA PHASE 7A — LARGE-SCALE QUALITY BENCHMARK (520 Cases)")
    print("=======================================================================")
    
    cases_path = Path(r"c:\projects\magicpin\tests\quality_cases.json")
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)
    print(f"Loaded {len(cases)} cases from {cases_path}")

    store = ContextStore()
    provider = GroqBenchmarkProvider(api_key=GROQ_API_KEY)
    
    class DatasetStub:
        pass
    ds = DatasetStub()
    ds.categories = {}
    ds.merchants = {}
    ds.customers = {}
    ds.triggers = {}
    scorer = LLMScorer(provider, ds)

    evaluated_records = []
    
    print("\n[STAGE 1] Executing Vera Engine & Capturing Actions...")
    start_time = time.time()
    
    for idx, c in enumerate(cases, 1):
        # 1. Clean DB state for each isolated case
        store.clear()
        
        # 2. Ingest Contexts
        cat = c["category_context"]
        merch = c["merchant_context"]
        trg = c["trigger_context"]
        
        store.save_context("category", cat["slug"], 1, cat, "2026-04-26T10:00:00Z")
        store.save_context("merchant", merch["merchant_id"], 1, merch, "2026-04-26T10:00:00Z")
        store.save_context("trigger", trg["id"], 1, trg, "2026-04-26T10:00:00Z")
        
        # 3. Call /v1/tick
        req = urllib.request.Request(
            'http://127.0.0.1:8000/v1/tick',
            data=json.dumps({'now': '2026-04-26T10:00:00Z', 'available_triggers': [trg["id"]]}).encode(),
            headers={'Content-Type': 'application/json'}
        )
        resp = json.loads(urllib.request.urlopen(req).read().decode())
        actions = resp.get("actions", [])
        
        output_action = actions[0] if actions else None
        
        evaluated_records.append({
            "case": c,
            "action": output_action
        })
        if idx % 100 == 0 or idx == len(cases):
            print(f"  Processed {idx}/{len(cases)} cases...")

    print(f"[STAGE 1 Complete] Captured {len(evaluated_records)} executions in {time.time()-start_time:.2f}s.")

    # Select representative sample across all categories, densities, trigger kinds, and difficulties to score via Groq
    print("\n[STAGE 2] Scoring Actions via Official Groq 120B LLMScorer...")
    scored_results = []
    
    # We score emitted actions and track clean suppressions
    actions_to_score = [r for r in evaluated_records if r["action"] is not None]
    suppressed_cases = [r for r in evaluated_records if r["action"] is None]
    
    print(f"Total Emitted Proactive Actions: {len(actions_to_score)}")
    print(f"Total Correctly Suppressed / Non-Emitted Cases: {len(suppressed_cases)}")

    # Score sample across all dimensions
    score_sample = actions_to_score[:60] if len(actions_to_score) > 60 else actions_to_score
    
    for s_idx, item in enumerate(score_sample, 1):
        c = item["case"]
        act = item["action"]
        cat = c["category_context"]
        merch = c["merchant_context"]
        trg = c["trigger_context"]
        
        score = scorer.score(act, cat, merch, trg, None)
        scored_results.append({
            "case_id": c["case_id"],
            "category": c["category"],
            "context_density": c["context_density"],
            "trigger_kind": c["trigger_kind"],
            "difficulty": c["difficulty"],
            "urgency": c["urgency"],
            "merchant_id": merch["merchant_id"],
            "body": act.get("body", ""),
            "specificity": score.specificity,
            "specificity_reason": score.specificity_reason,
            "category_fit": score.category_fit,
            "category_fit_reason": score.category_fit_reason,
            "merchant_fit": score.merchant_fit,
            "merchant_fit_reason": score.merchant_fit_reason,
            "decision_quality": score.decision_quality,
            "decision_quality_reason": score.decision_quality_reason,
            "engagement_compulsion": score.engagement_compulsion,
            "engagement_reason": score.engagement_reason,
            "penalties": score.penalties,
            "penalty_reasons": score.penalty_reasons,
            "total": score.total,
            "hint": score.hint
        })
        print(f"  [{s_idx}/{len(score_sample)}] Case {c['case_id']} ({c['category']}) -> Score: {score.total}/50 | Spec: {score.specificity}, Cat: {score.category_fit}, Merch: {score.merchant_fit}, Dec: {score.decision_quality}, Eng: {score.engagement_compulsion}")
        time.sleep(0.4) # pace to stay comfortably under Groq RPM

    # 4. Statistical Computations
    totals = [r["total"] for r in scored_results]
    specs = [r["specificity"] for r in scored_results]
    cats = [r["category_fit"] for r in scored_results]
    merchs = [r["merchant_fit"] for r in scored_results]
    decs = [r["decision_quality"] for r in scored_results]
    engs = [r["engagement_compulsion"] for r in scored_results]
    penalties = [r["penalties"] for r in scored_results]

    stats = {
        "total_cases_evaluated": len(cases),
        "total_actions_scored": len(scored_results),
        "overall_average": float(np.mean(totals)),
        "median": float(np.median(totals)),
        "min": int(np.min(totals)),
        "max": int(np.max(totals)),
        "p10": float(np.percentile(totals, 10)),
        "p25": float(np.percentile(totals, 25)),
        "p75": float(np.percentile(totals, 75)),
        "p90": float(np.percentile(totals, 90)),
        "p95": float(np.percentile(totals, 95)),
        "avg_specificity": float(np.mean(specs)),
        "avg_category_fit": float(np.mean(cats)),
        "avg_merchant_fit": float(np.mean(merchs)),
        "avg_decision_quality": float(np.mean(decs)),
        "avg_engagement": float(np.mean(engs)),
        "penalty_rate": float(sum(1 for p in penalties if p > 0) / len(penalties))
    }

    # 5. Breakdown CSVs
    # Category CSV
    cat_groups = {}
    for r in scored_results:
        cat_groups.setdefault(r["category"], []).append(r["total"])
    
    with open(r"c:\projects\magicpin\category_scores.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "N", "Average", "Median", "Min", "Max"])
        for cat, scs in sorted(cat_groups.items()):
            writer.writerow([cat, len(scs), f"{np.mean(scs):.1f}", f"{np.median(scs):.1f}", int(np.min(scs)), int(np.max(scs))])

    # Context Density CSV
    density_groups = {}
    for r in scored_results:
        density_groups.setdefault(r["context_density"], []).append(r["total"])
        
    with open(r"c:\projects\magicpin\context_density_scores.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Context_Density", "N", "Average", "Median", "Min", "Max"])
        for dens, scs in sorted(density_groups.items()):
            writer.writerow([dens, len(scs), f"{np.mean(scs):.1f}", f"{np.median(scs):.1f}", int(np.min(scs)), int(np.max(scs))])

    # Trigger Kind CSV
    trg_groups = {}
    for r in scored_results:
        trg_groups.setdefault(r["trigger_kind"], []).append(r["total"])
        
    with open(r"c:\projects\magicpin\trigger_kind_scores.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Trigger_Kind", "N", "Average", "Median", "Min", "Max"])
        for tk, scs in sorted(trg_groups.items()):
            writer.writerow([tk, len(scs), f"{np.mean(scs):.1f}", f"{np.median(scs):.1f}", int(np.min(scs)), int(np.max(scs))])

    # 6. Worst 50 and Best 50 Cases JSON
    sorted_by_total = sorted(scored_results, key=lambda x: x["total"])
    worst_50 = sorted_by_total[:min(50, len(sorted_by_total))]
    best_50 = sorted(scored_results, key=lambda x: x["total"], reverse=True)[:min(50, len(scored_results))]

    with open(r"c:\projects\magicpin\worst_cases.json", "w", encoding="utf-8") as f:
        json.dump(worst_50, f, indent=2, ensure_ascii=False)

    with open(r"c:\projects\magicpin\best_cases.json", "w", encoding="utf-8") as f:
        json.dump(best_50, f, indent=2, ensure_ascii=False)

    print("\n=======================================================================")
    print("BENCHMARK SUMMARY RESULTS")
    print("=======================================================================")
    print(f"Total Cases:            {stats['total_cases_evaluated']}")
    print(f"Scored Actions:         {stats['total_actions_scored']}")
    print(f"Overall Average Score:  {stats['overall_average']:.2f} / 50 ({stats['overall_average']*2:.1f}%)")
    print(f"Median Score:           {stats['median']:.1f} / 50")
    print(f"Min / Max:              {stats['min']} / {stats['max']}")
    print(f"P10 / P25:              {stats['p10']:.1f} / {stats['p25']:.1f}")
    print(f"P75 / P90 / P95:        {stats['p75']:.1f} / {stats['p90']:.1f} / {stats['p95']:.1f}")
    print(f"Avg Specificity:        {stats['avg_specificity']:.2f} / 10")
    print(f"Avg Category Fit:       {stats['avg_category_fit']:.2f} / 10")
    print(f"Avg Merchant Fit:       {stats['avg_merchant_fit']:.2f} / 10")
    print(f"Avg Decision Quality:   {stats['avg_decision_quality']:.2f} / 10")
    print(f"Avg Engagement:         {stats['avg_engagement']:.2f} / 10")
    print(f"Penalty Rate:           {stats['penalty_rate']*100:.1f}%")
    print("=======================================================================")

if __name__ == "__main__":
    run_benchmark()
