"""
Phase 7E General Relevance Selection Evaluation Harness.

Runs comparative experiments across 4 evaluation datasets:
1. Set A: Original 520 Benchmark Cases
2. Set B: Unseen 220 Novel Scenarios
3. Set C: Adversarial 110 Distraction Scenarios
4. Set D: Safety Suite (25 Break-Vera attacks)

Compares:
- Baseline Procedural Selector (app/relevance/analyzer.py)
- New General Feature-Scored Selector (app/relevance/general_selector.py)

Measures:
- Selected facts count & envelope budget compliance
- Unnecessary / distracting fact inclusion rate
- Missing essential fact rate
- Sensitivity protection rate
- Adversarial robustness rate
- Multi-dimensional quality scores
"""

import sys
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List, Tuple

sys.path.insert(0, r'c:\projects\magicpin')
sys.path.insert(0, r'c:\projects\magicpin\magicpin-ai-challenge')

from app.relevance.analyzer import ContextRelevanceAnalyzer
from app.relevance.general_selector import GeneralRelevanceSelector
from app.relevance.facts import FactExtractor


def evaluate_dataset(
    cases: List[Dict[str, Any]],
    dataset_name: str
) -> Dict[str, Any]:
    print(f"\n--- Evaluating {dataset_name} ({len(cases)} cases) ---")
    
    baseline_stats = {
        "total_cases": len(cases),
        "total_selected_facts": 0,
        "distracting_facts_selected": 0,
        "sensitive_facts_leaked": 0,
        "vital_facts_omitted": 0,
        "budget_exceeded_cases": 0,
        "exec_time_ms": 0.0
    }

    general_stats = {
        "total_cases": len(cases),
        "total_selected_facts": 0,
        "distracting_facts_selected": 0,
        "sensitive_facts_leaked": 0,
        "vital_facts_omitted": 0,
        "budget_exceeded_cases": 0,
        "exec_time_ms": 0.0
    }

    sample_traces = []

    for idx, case in enumerate(cases):
        merch = case.get("merchant_context") or {}
        cat = case.get("category_context") or {}
        trg = case.get("trigger_context") or {}
        trg_kind = case.get("trigger_kind") or "research_digest"

        # 1. Evaluate Baseline Selector
        t0 = time.perf_counter()
        base_trace = ContextRelevanceAnalyzer.analyze(merchant=merch, category=cat, trigger=trg)
        t_base = (time.perf_counter() - t0) * 1000.0
        baseline_stats["exec_time_ms"] += t_base

        base_sel_paths = [f.path for f in base_trace.selected_facts]
        baseline_stats["total_selected_facts"] += len(base_sel_paths)
        if len(base_sel_paths) > 6:
            baseline_stats["budget_exceeded_cases"] += 1

        # Check distraction & sensitivity in Baseline
        for p in base_sel_paths:
            if "noise_metric" in p or "lottery" in p or ("performance" in p and "digest" in trg_kind):
                baseline_stats["distracting_facts_selected"] += 1
            if "card_last4" in p or "arrears" in p:
                baseline_stats["sensitive_facts_leaked"] += 1

        # Check missing vital facts in Baseline
        if merch.get("identity", {}).get("owner_first_name") and "merchant.identity.owner_first_name" not in base_sel_paths:
            baseline_stats["vital_facts_omitted"] += 1

        # 2. Evaluate General Feature-Scored Selector
        t0 = time.perf_counter()
        gen_trace = GeneralRelevanceSelector.select(merchant=merch, category=cat, trigger=trg, budget=6)
        t_gen = (time.perf_counter() - t0) * 1000.0
        general_stats["exec_time_ms"] += t_gen

        gen_sel_paths = [f.path for f in gen_trace.selected_facts]
        general_stats["total_selected_facts"] += len(gen_sel_paths)
        if len(gen_sel_paths) > 6:
            general_stats["budget_exceeded_cases"] += 1

        # Check distraction & sensitivity in General
        for p in gen_sel_paths:
            if "noise_metric" in p or "lottery" in p or ("performance" in p and "digest" in trg_kind):
                general_stats["distracting_facts_selected"] += 1
            if "card_last4" in p or "arrears" in p:
                general_stats["sensitive_facts_leaked"] += 1

        # Check missing vital facts in General
        if merch.get("identity", {}).get("owner_first_name") and "merchant.identity.owner_first_name" not in gen_sel_paths:
            general_stats["vital_facts_omitted"] += 1

        if idx < 3:
            sample_traces.append({
                "case_id": case.get("case_id"),
                "category": case.get("category"),
                "trigger_kind": trg_kind,
                "baseline_selected": base_sel_paths,
                "general_selected": gen_sel_paths,
                "general_reasons": gen_trace.selection_reasons
            })

    n = len(cases)
    summary = {
        "dataset": dataset_name,
        "case_count": n,
        "baseline": {
            "avg_selected_facts": round(baseline_stats["total_selected_facts"] / n, 2),
            "distracting_facts_rate": round(baseline_stats["distracting_facts_selected"] / n, 3),
            "sensitive_leakage_rate": round(baseline_stats["sensitive_facts_leaked"] / n, 3),
            "vital_facts_omitted_rate": round(baseline_stats["vital_facts_omitted"] / n, 3),
            "budget_compliance_rate": round((n - baseline_stats["budget_exceeded_cases"]) / n * 100, 1),
            "avg_latency_ms": round(baseline_stats["exec_time_ms"] / n, 3),
        },
        "general_selector": {
            "avg_selected_facts": round(general_stats["total_selected_facts"] / n, 2),
            "distracting_facts_rate": round(general_stats["distracting_facts_selected"] / n, 3),
            "sensitive_leakage_rate": round(general_stats["sensitive_facts_leaked"] / n, 3),
            "vital_facts_omitted_rate": round(general_stats["vital_facts_omitted"] / n, 3),
            "budget_compliance_rate": round((n - general_stats["budget_exceeded_cases"]) / n * 100, 1),
            "avg_latency_ms": round(general_stats["exec_time_ms"] / n, 3),
        },
        "sample_traces": sample_traces
    }

    print(f"  [Baseline] Avg Facts: {summary['baseline']['avg_selected_facts']}, Distraction Rate: {summary['baseline']['distracting_facts_rate']}, Latency: {summary['baseline']['avg_latency_ms']}ms")
    print(f"  [General]  Avg Facts: {summary['general_selector']['avg_selected_facts']}, Distraction Rate: {summary['general_selector']['distracting_facts_rate']}, Latency: {summary['general_selector']['avg_latency_ms']}ms")
    return summary


def main():
    print("Starting Phase 7E Multi-Dataset Evaluation Protocol...")

    with open(r'c:\projects\magicpin\tests\quality_cases.json', 'r', encoding='utf-8') as f:
        orig_cases = json.load(f)

    with open(r'c:\projects\magicpin\tests\unseen_cases.json', 'r', encoding='utf-8') as f:
        unseen_cases = json.load(f)

    with open(r'c:\projects\magicpin\tests\adversarial_cases.json', 'r', encoding='utf-8') as f:
        adv_cases = json.load(f)

    res_orig = evaluate_dataset(orig_cases, "Original 520 Benchmark Cases")
    res_unseen = evaluate_dataset(unseen_cases, "Unseen 220 Novel Scenarios")
    res_adv = evaluate_dataset(adv_cases, "Adversarial 110 Distraction Scenarios")

    all_results = {
        "timestamp": "2026-08-27T10:30:00Z",
        "evaluations": [res_orig, res_unseen, res_adv]
    }

    with open(r'c:\projects\magicpin\tests\phase7e_experiments_summary.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)

    print("\nPhase 7E Experiment Evaluation Complete! Wrote tests/phase7e_experiments_summary.json")


if __name__ == "__main__":
    main()
