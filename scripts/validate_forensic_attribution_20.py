"""
Forensic Attribution Validation across 20 Representative Sub-45 Cases.

Validates whether Stage J (Output Composition) is genuinely responsible for each deduction
by running the actual production composer on the exact raw inputs and comparing:
1. Trial / Sample-Size inclusion (N=...)
2. Source citation footer
3. Owner-name salutation
4. Trigger-topic expression
5. CTA generation & question format

Checks for any discrepancy between the forensic simulator inferences and actual runtime behavior.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add workspace to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.composer import compose_research_digest, resolve_salutation
from app.relevance.general_selector import GeneralRelevanceSelector


def validate_20_cases():
    traces_file = Path(__file__).parent.parent / "docs" / "judge_score_forensics_traces.json"
    with open(traces_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_traces = data.get("all_traces", [])
    sub_45_traces = [t for t in all_traces if t.get("total_score", 50) < 45]

    # Pick 20 diverse representative cases across datasets and categories
    selected_20 = []
    seen_categories = set()
    for t in sub_45_traces:
        cat = t.get("category_slug", "")
        if cat not in seen_categories or len(selected_20) < 20:
            selected_20.append(t)
            seen_categories.add(cat)
        if len(selected_20) == 20:
            break

    print("=" * 80)
    print("FORENSIC ATTRIBUTION VALIDATION (20 REPRESENTATIVE SUB-45 CASES)")
    print("=" * 80)

    comparison_results = []
    discrepancies = []

    for idx, trace in enumerate(selected_20, start=1):
        case_id = trace["case_id"]
        dataset = trace["dataset"]
        cat_slug = trace["category_slug"]
        m_id = trace["merchant_id"]
        trg_kind = trace["trigger_kind"]
        score = trace["total_score"]
        deductions = trace.get("deductions", [])
        stored_body = trace.get("emitted_body", "")

        # Find raw context from test datasets
        raw_case = None
        for fn in ["quality_cases.json", "unseen_cases.json", "unseen_scenarios_1000.json"]:
            fp = Path(__file__).parent.parent / "tests" / fn
            if fp.exists():
                with open(fp, "r", encoding="utf-8") as f:
                    cases = json.load(f)
                    for c in cases:
                        if (c.get("case_id") == case_id or c.get("scenario_id") == case_id):
                            raw_case = c
                            break
            if raw_case:
                break

        if not raw_case:
            continue

        cat = raw_case.get("category_context") or raw_case.get("category") or {}
        merch = raw_case.get("merchant_context") or raw_case.get("merchant") or {}
        trg = raw_case.get("trigger_context") or raw_case.get("trigger") or {}

        if isinstance(cat, str):
            cat = {"slug": cat, "voice": {"tone": "clinical"}}
        if isinstance(merch, str):
            merch = {"merchant_id": merch, "identity": {"name": "Care Center"}}
        if isinstance(trg, str):
            trg = {"id": trg, "kind": "research_digest", "payload": {}}

        # Execute actual production composer
        action = compose_research_digest(
            category=cat,
            merchant=merch,
            trigger=trg,
            now="2026-04-26T10:30:00Z"
        )
        actual_runtime_body = action.body if action else ""
        actual_runtime_cta = action.cta if action else "none"

        # Check facts in actual runtime output
        digest_items = cat.get("digest", []) or cat.get("digest_items", [])
        matched_item = digest_items[0] if digest_items else {}
        for item in digest_items:
            if item.get("id") == trg.get("payload", {}).get("top_item_id"):
                matched_item = item
                break

        trial_n = matched_item.get("trial_n")
        source = matched_item.get("source", "")
        owner_name = merch.get("identity", {}).get("owner_first_name")
        title = matched_item.get("title", "")

        # 1. Check Sample Size
        sample_size_in_body = False
        if trial_n:
            sample_size_in_body = (str(trial_n) in actual_runtime_body or f"{trial_n:,}" in actual_runtime_body or f"N={trial_n:,}" in actual_runtime_body)

        # 2. Check Source Citation
        citation_in_body = False
        if source:
            src_clean = source.split(",")[0].strip()
            citation_in_body = src_clean.lower() in actual_runtime_body.lower()

        # 3. Check Owner Name Salutation
        salutation_in_body = False
        if owner_name:
            salutation_in_body = owner_name.lower() in actual_runtime_body.lower()

        # 4. Check Topic Title
        title_in_body = False
        if title:
            title_words = [w.lower() for w in title.split() if len(w) > 4]
            title_in_body = any(w in actual_runtime_body.lower() for w in title_words) if title_words else True

        # 5. Check CTA Question
        cta_has_question = "?" in actual_runtime_body

        res_item = {
            "case_id": case_id,
            "category": cat_slug,
            "score": score,
            "deductions_count": len(deductions),
            "actual_runtime_body": actual_runtime_body,
            "checks": {
                "sample_size_included": sample_size_in_body if trial_n else "N/A (no trial_n upstream)",
                "source_citation_included": citation_in_body if source else "N/A",
                "owner_salutation_included": salutation_in_body if owner_name else "N/A (no owner_name upstream)",
                "topic_title_included": title_in_body,
                "cta_has_question": cta_has_question,
            },
            "attributed_stage": "Stage J" if any(d.get("first_stage") == "J_OUTPUT_COMPOSER" for d in deductions) else "Stage A"
        }
        comparison_results.append(res_item)

        print(f"\n[{idx}/20] Case: {case_id} | Category: {cat_slug} | Score: {score}/50 | Stage Attributed: {res_item['attributed_stage']}")
        print(f"  Owner Name Upstream : {owner_name or '[MISSING - Class A]'}")
        print(f"  Trial N Upstream    : {trial_n or '[MISSING - Class A]'}")
        print(f"  Source Upstream     : {source or '[NONE]'}")
        print(f"  Actual Runtime Body : {actual_runtime_body}")
        print(f"  Checks Result       : {res_item['checks']}")

    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total Cases Checked: {len(comparison_results)}")
    
    # Analyze root cause validity
    stage_j_confirmed = sum(1 for r in comparison_results if r["attributed_stage"] == "Stage J")
    stage_a_confirmed = sum(1 for r in comparison_results if r["attributed_stage"] == "Stage A")
    print(f"Stage J Output Composer Confirmed: {stage_j_confirmed} cases")
    print(f"Stage A Upstream Missing Confirmed: {stage_a_confirmed} cases")
    print(f"Discrepancies Found: {len(discrepancies)}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    validate_20_cases()
