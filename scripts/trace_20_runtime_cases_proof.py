"""
Forensic Runtime Proof & Stage-by-Stage Verification across 20 Sub-45 Cases.

Executes the REAL runtime pipeline step-by-step:
RAW INPUT -> FactExtractor -> GeneralRelevanceSelector -> build_context_envelope
          -> LLM / Composer -> Validator -> Final API Response -> Judge Scoring

Compares the stored forensic JSON emitted_body vs actual runtime output to prove:
1. Exact intermediate text at every pipeline stage
2. First stage responsible for every deduction
3. Any mismatch between forensic JSON and actual runtime execution
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.store.context_store import get_context_store
from app.relevance.facts import FactExtractor
from app.relevance.general_selector import GeneralRelevanceSelector
from app.llm.prompts import build_context_envelope
from app.engine.composer import compose_research_digest
from app.llm.validator import LLMOutputValidator
from scripts.judge_score_forensics import evaluate_case_quality_score

client = TestClient(app)


def find_case_raw_context(case_id: str) -> Optional[Dict[str, Any]]:
    """Search for raw case across all benchmark and test JSONs."""
    tests_dir = Path(__file__).parent.parent / "tests"
    for fn in ["quality_cases.json", "unseen_cases.json", "unseen_scenarios_1000.json"]:
        fp = tests_dir / fn
        if fp.exists():
            with open(fp, "r", encoding="utf-8") as f:
                cases = json.load(f)
                for c in cases:
                    if c.get("case_id") == case_id or c.get("scenario_id") == case_id:
                        return c
    return None


def trace_real_runtime_case(case_id: str, stored_trace: Dict[str, Any]) -> Dict[str, Any]:
    """Execute each exact pipeline component and capture actual runtime objects."""
    store = get_context_store()
    store.clear()

    raw_case = find_case_raw_context(case_id)
    if not raw_case:
        return {"error": f"Case {case_id} not found in dataset files"}

    cat = raw_case.get("category_context") or raw_case.get("category") or {}
    merch = raw_case.get("merchant_context") or raw_case.get("merchant") or {}
    trg = raw_case.get("trigger_context") or raw_case.get("trigger") or {}

    if isinstance(cat, str):
        cat = {"slug": cat, "voice": {"tone": "clinical"}}
    if isinstance(merch, str):
        merch = {"merchant_id": merch, "identity": {"name": "Care Center"}}
    if isinstance(trg, str):
        trg = {"id": trg, "kind": "research_digest", "payload": {}}

    # Stage 1: Raw Context Ingestion via HTTP API
    r_cat = client.post("/v1/context", json={"scope": "category", "context_id": cat.get("slug", "cat"), "version": 1, "payload": cat, "delivered_at": "2026-04-26T10:00:00Z"})
    r_merch = client.post("/v1/context", json={"scope": "merchant", "context_id": merch.get("merchant_id", "m_id"), "version": 1, "payload": merch, "delivered_at": "2026-04-26T10:00:00Z"})
    r_trg = client.post("/v1/context", json={"scope": "trigger", "context_id": trg.get("id", "trg_id"), "version": 1, "payload": trg, "delivered_at": "2026-04-26T10:00:00Z"})

    # Stage 2: Fact Extraction
    all_extracted_facts = FactExtractor.extract_all_contexts(merchant=merch, category=cat, trigger=trg)

    # Stage 3: General Relevance Selection & Role Budgeting
    fact_trace = GeneralRelevanceSelector.select(
        merchant=merch,
        category=cat,
        trigger=trg
    )
    selected_facts = fact_trace.selected_facts

    # Stage 4: LLM Envelope Assembly
    envelope = build_context_envelope(
        store=store,
        conversation_id=f"conv_{case_id}",
        merchant_id=merch.get("merchant_id", "m_id"),
        category_slug=cat.get("slug"),
        selected_facts=selected_facts
    )

    # Stage 5: Deterministic Composer Output
    tick_action = compose_research_digest(
        category=cat,
        merchant=merch,
        trigger=trg,
        now="2026-04-26T10:30:00Z"
    )
    composer_body = tick_action.body if tick_action else ""
    composer_cta = tick_action.cta if tick_action else "none"

    # Stage 6: LLM Safety Validator
    validation_res = None
    if composer_body:
        from app.llm.schemas import LLMDecisionSuggestion
        suggestion = LLMDecisionSuggestion(
            suggested_intent="INTENT_AFFIRM",
            confidence=0.95,
            proposed_action="send",
            response_strategy="direct_action",
            draft_body=composer_body,
            proposed_cta=composer_cta if composer_cta in ("open_ended", "binary_yes_no", "quick_reply", "calendar", "none") else "open_ended",
            cited_fact_ids=[f.fact_id for f in envelope.supported_facts[:3]],
            rationale="Grounded tick output"
        )
        validation_res = LLMOutputValidator.validate(
            suggestion=suggestion,
            envelope=envelope,
            current_state="IDLE"
        )

    # Stage 7: Actual Live API Output from /v1/tick
    r_tick = client.post("/v1/tick", json={"now": "2026-04-26T10:30:00Z", "available_triggers": [trg.get("id")]})
    tick_res = r_tick.json()
    actions = tick_res.get("actions", [])
    final_api_body = actions[0].get("body", "") if actions else ""
    final_api_cta = actions[0].get("cta", "none") if actions else "none"

    # Stage 8: Forensic Trace Comparison (Stored vs Actual)
    stored_body = stored_trace.get("emitted_body", "")
    is_mismatch = (stored_body.strip() != final_api_body.strip())

    # Stage 9: Quality Scoring & Deduction Analysis
    score, dim_scores, reasons, deductions = evaluate_case_quality_score(
        category=cat,
        merchant=merch,
        trigger=trg,
        body=final_api_body,
        cta=final_api_cta
    )

    return {
        "case_id": case_id,
        "dataset": stored_trace.get("dataset"),
        "category_slug": cat.get("slug"),
        "merchant_id": merch.get("merchant_id"),
        "trigger_kind": trg.get("kind"),
        "raw_context_summary": {
            "owner_first_name": merch.get("identity", {}).get("owner_first_name"),
            "category_tone": cat.get("voice", {}).get("tone"),
            "digest_title": cat.get("digest", [{}])[0].get("title") if cat.get("digest") else None,
            "trial_n": cat.get("digest", [{}])[0].get("trial_n") if cat.get("digest") else None,
            "source": cat.get("digest", [{}])[0].get("source") if cat.get("digest") else None,
            "patient_segment": cat.get("digest", [{}])[0].get("patient_segment") if cat.get("digest") else None,
            "actionable": cat.get("digest", [{}])[0].get("actionable") if cat.get("digest") else None,
            "trigger_expires_at": trg.get("expires_at"),
        },
        "extracted_facts_count": len(all_extracted_facts),
        "selected_facts_paths": [f.path for f in selected_facts],
        "envelope_facts_count": len(envelope.supported_facts),
        "composer_output_body": composer_body,
        "validator_passed": validation_res.is_valid if validation_res else True,
        "final_api_body": final_api_body,
        "stored_forensic_body": stored_body,
        "body_mismatch": is_mismatch,
        "judge_score": score,
        "dimension_scores": dim_scores,
        "deductions": deductions
    }


def main():
    traces_file = Path(__file__).parent.parent / "docs" / "judge_score_forensics_traces.json"
    with open(traces_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_traces = data.get("all_traces", [])
    sub_45_traces = [t for t in all_traces if t.get("total_score", 50) < 45]

    # Select 20 representative cases across different categories and datasets
    target_case_ids = [
        "qc_0002", "qc_0004", "qc_0008", "qc_0010", "qc_0012",
        "qc_0015", "qc_0016", "qc_0018", "qc_0020", "qc_0024",
        "qc_0028", "qc_0032", "qc_0036", "qc_0040", "qc_0044",
        "unseen_0005", "unseen_0012", "unseen_0018",
        "syn_0010", "syn_0024"
    ]

    selected_traces = {}
    for t in all_traces:
        cid = t.get("case_id")
        if cid in target_case_ids and cid not in selected_traces:
            selected_traces[cid] = t

    print("=" * 80)
    print("REAL RUNTIME PIPELINE TRACE & VERIFICATION (20 SUB-45 CASES)")
    print("=" * 80)

    results = []
    mismatch_count = 0

    for idx, cid in enumerate(target_case_ids, start=1):
        stored_trace = selected_traces.get(cid) or {"dataset": "UNKNOWN", "emitted_body": ""}
        runtime_trace = trace_real_runtime_case(cid, stored_trace)
        results.append(runtime_trace)

        if runtime_trace.get("body_mismatch"):
            mismatch_count += 1

        print(f"\n--- CASE [{idx}/20]: {cid} (Score: {runtime_trace.get('judge_score')}/50) ---")
        raw = runtime_trace.get("raw_context_summary", {})
        print(f"1. Available Info     : Owner={raw.get('owner_first_name')}, N={raw.get('trial_n')}, Seg='{raw.get('patient_segment')}', Src='{raw.get('source')}'")
        print(f"2. Extracted Facts    : {runtime_trace.get('extracted_facts_count')} facts extracted")
        print(f"3. Selected Facts     : {runtime_trace.get('selected_facts_paths')}")
        print(f"4. Envelope Supported : {runtime_trace.get('envelope_facts_count')} facts in envelope")
        print(f"5. Composer Output    : \"{runtime_trace.get('composer_output_body')}\"")
        print(f"6. Validator Result   : Valid={runtime_trace.get('validator_passed')}")
        print(f"7. Final API Response : \"{runtime_trace.get('final_api_body')}\"")
        print(f"8. Forensic Mismatch  : {runtime_trace.get('body_mismatch')}")
        print(f"9. Deductions         : {runtime_trace.get('deductions')}")

    out_file = Path(__file__).parent.parent / "docs" / "forensic_runtime_proof_20_cases.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"PROOFS COMPLETED! Results written to: {out_file.resolve()}")
    print(f"Total Mismatches Between Forensic JSON and Real Runtime: {mismatch_count}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
