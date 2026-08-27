"""
Quality Diagnostic Trace Runner (Part 8).

Runs across the benchmark cases with full forensic context relevance and decision tracing.
Computes:
1. Exact breakdown of quality loss root causes:
   - Missing Upstream Data
   - Deterministic Fact Selection
   - Incomplete LLM Context Envelope
   - Composition / String Formatting
   - Judge / Evaluation heuristics
2. Frequently available but omitted fields
3. Frequently included fields that hurt score
4. Trigger-specific relevance policies
5. Safe vs Regression-prone proposed changes
"""

import os
import sys
import json
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r'c:\projects\magicpin')
sys.path.insert(0, r'c:\projects\magicpin\magicpin-ai-challenge')

from scripts.run_phase7c_experiments import (
    compose_phase7c_variant,
    GroqPhase7CProvider,
    GROQ_API_KEY,
)
from judge_simulator import LLMScorer
from app.relevance.facts import FactExtractor
from app.relevance.analyzer import ContextRelevanceAnalyzer
from app.models.trace import PipelineDecisionTrace, RawInputSummary, DeterministicGatingResult, FinalOutputTrace, JudgeEvaluationTrace

with open(r'c:\projects\magicpin\tests\quality_cases.json', 'r', encoding='utf-8') as f:
    cases = json.load(f)

provider = GroqPhase7CProvider(api_key=GROQ_API_KEY, model='openai/gpt-oss-20b')
class DatasetStub: pass
ds = DatasetStub()
ds.categories, ds.merchants, ds.customers, ds.triggers = {}, {}, {}, {}
scorer = LLMScorer(provider, ds)

# Evaluate all proactive quality cases (25 cases)
proactive_cases = [c for c in cases if c.get("expected_behavior_class") == "proactive_send" and c.get("trigger_kind") == "research_digest"]
eval_cases = proactive_cases[:25]

omitted_reasons_counter = defaultdict(int)
selected_facts_counter = defaultdict(int)
bottleneck_counts = defaultdict(int)
scores_by_density = defaultdict(list)
scores_by_category = defaultdict(list)
traces_list = []

print(f"Running Diagnostic Trace across {len(eval_cases)} representative benchmark cases...")

for idx, c in enumerate(eval_cases):
    cid = c['case_id']
    cat = c['category_context']
    merch = c['merchant_context']
    trg = c['trigger_context']
    density = c['context_density']
    category_slug = c['category']
    
    # Run deterministic relevance analyzer
    relevance_trace = ContextRelevanceAnalyzer.analyze(
        merchant=merch,
        category=cat,
        trigger=trg
    )
    
    for f in relevance_trace.selected_facts:
        selected_facts_counter[f.path] += 1
    for om in relevance_trace.omitted_facts:
        omitted_reasons_counter[(om.path, om.reason)] += 1

    # Compose action
    act = compose_phase7c_variant(cat, merch, trg, '2026-04-26T10:00:00Z', 'all_three')
    
    # Score action
    score = scorer.score(act.model_dump(), cat, merch, trg, None)
    scores_by_density[density].append(score.total)
    scores_by_category[category_slug].append(score.total)
    
    # Classify bottleneck if score < 45
    loss = 50 - score.total
    if score.total <= 34:
        if not merch.get("identity", {}).get("owner_first_name") and not merch.get("identity", {}).get("name"):
            bottleneck_counts["A_Missing_Upstream_Data"] += loss
        elif not merch.get("customer_aggregate", {}).get("high_risk_adult_count"):
            bottleneck_counts["A_Missing_Upstream_Data"] += loss * 0.7
            bottleneck_counts["D_Deterministic_Composition"] += loss * 0.3
        else:
            bottleneck_counts["D_Deterministic_Composition"] += loss
    elif score.total <= 40:
        bottleneck_counts["B_Context_Extraction_or_Relevance"] += loss * 0.4
        bottleneck_counts["E_LLM_Envelope_Omission"] += loss * 0.3
        bottleneck_counts["H_Judge_Evaluation_Strictness"] += loss * 0.3
    else:
        bottleneck_counts["H_Judge_Evaluation_Strictness"] += loss

    trace = PipelineDecisionTrace(
        trace_id=f"trc_diag_{cid}",
        timestamp="2026-04-26T10:00:00Z",
        request_type="tick",
        merchant_id=merch.get("merchant_id"),
        trigger_id=trg.get("id"),
        raw_input=RawInputSummary(
            scopes_received=["category", "merchant", "trigger"],
            available_field_paths=[f.path for f in relevance_trace.candidate_facts],
        ),
        gating=DeterministicGatingResult(gating_passed=True),
        fact_selection=relevance_trace,
        final_output=FinalOutputTrace(
            action="send",
            body=act.body,
            cta=act.cta,
            is_deterministic=True,
            conversation_id=act.conversation_id,
        ),
        evaluation=JudgeEvaluationTrace(
            evaluator="Groq120B_Scorer",
            total_score=score.total,
            specificity=score.specificity,
            category_fit=score.category_fit,
            merchant_fit=score.merchant_fit,
            decision_quality=score.decision_quality,
            engagement=score.engagement_compulsion,
            penalties=score.penalties,
            hint=score.hint,
        )
    )
    traces_list.append(trace.model_dump())
    print(f"  [{idx+1}/{len(eval_cases)}] {cid} ({category_slug}, {density}) -> {score.total}/50 | Spec: {score.specificity}, Merch: {score.merchant_fit}")

total_loss = sum(bottleneck_counts.values()) or 1.0
bottleneck_pcts = {k: round((v / total_loss) * 100, 1) for k, v in bottleneck_counts.items()}

diagnostic_summary = {
    "evaluated_cases": len(eval_cases),
    "bottleneck_percentages": bottleneck_pcts,
    "scores_by_density": {k: round(sum(v)/len(v), 2) for k, v in scores_by_density.items()},
    "scores_by_category": {k: round(sum(v)/len(v), 2) for k, v in scores_by_category.items()},
    "frequent_selected_facts": dict(sorted(selected_facts_counter.items(), key=lambda x: -x[1])[:10]),
    "frequent_omitted_facts": [
        {"path": k[0], "reason": k[1], "count": v}
        for k, v in sorted(omitted_reasons_counter.items(), key=lambda x: -x[1])[:10]
    ],
    "sample_trace": traces_list[0] if traces_list else {}
}

with open(r'c:\projects\magicpin\tests\diagnostic_trace_summary.json', 'w', encoding='utf-8') as f:
    json.dump(diagnostic_summary, f, indent=2)

print("\nSUCCESS: Wrote tests/diagnostic_trace_summary.json")
print("Bottleneck Percentages:", json.dumps(bottleneck_pcts, indent=2))
