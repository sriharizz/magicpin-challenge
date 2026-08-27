import os
import sys
import json
from pathlib import Path

sys.path.insert(0, r'c:\projects\magicpin')
sys.path.insert(0, r'c:\projects\magicpin\magicpin-ai-challenge')

from scripts.run_phase7c_experiments import (
    compose_phase7c_variant,
    resolve_conditional_identity,
    resolve_context_aware_cta,
    GroqPhase7CProvider,
    GROQ_API_KEY
)
from judge_simulator import LLMScorer
from app.llm.schemas import LLMContextEnvelope, MerchantEnvelope, CategoryEnvelope, CategoryVoiceEnvelope, DigestItemEnvelope, SupportedFact, TurnHistoryItem
from app.llm.prompts import SYSTEM_PROMPT, format_user_prompt
from app.llm.validator import LLMOutputValidator

with open(r'c:\projects\magicpin\tests\quality_cases.json', 'r', encoding='utf-8') as f:
    cases = json.load(f)
case_map = {c['case_id']: c for c in cases}
target_ids = ['qc_0239', 'qc_0169', 'qc_0337', 'qc_0057', 'qc_0183']

provider = GroqPhase7CProvider(api_key=GROQ_API_KEY, model='openai/gpt-oss-20b')
class DatasetStub: pass
ds = DatasetStub()
ds.categories, ds.merchants, ds.customers, ds.triggers = {}, {}, {}, {}
scorer = LLMScorer(provider, ds)

output_data = {}

for cid in target_ids:
    c = case_map[cid]
    cat = c['category_context']
    merch = c['merchant_context']
    trg = c['trigger_context']
    
    # 1. Proactive Generation (All Three Variant)
    act = compose_phase7c_variant(cat, merch, trg, '2026-04-26T10:00:00Z', 'all_three')
    
    # Judge Score
    score = scorer.score(act.model_dump(), cat, merch, trg, None)
    
    # 2. Envelope & Prompt Construction for Inbound Turn
    # (Simulate merchant replying: "Can you tell me more about this study?")
    d0 = cat['digest'][0] if cat.get('digest') else None
    
    supported_facts = []
    if d0:
        if d0.get('trial_n'):
            supported_facts.append(SupportedFact(fact_id='F1', key='trial_n', value=str(d0['trial_n']), description='Total sample size in clinical trial'))
        if d0.get('source'):
            supported_facts.append(SupportedFact(fact_id='F2', key='source', value=str(d0['source']), description='Published journal citation'))
        if d0.get('summary'):
            supported_facts.append(SupportedFact(fact_id='F3', key='summary', value=str(d0['summary']), description='Core study conclusion'))
            
    envelope = LLMContextEnvelope(
        merchant=MerchantEnvelope(
            merchant_id=merch['merchant_id'],
            name=merch.get('identity', {}).get('name'),
            category_slug=merch.get('category_slug'),
            tone_preference=cat.get('voice', {}).get('tone')
        ),
        category=CategoryEnvelope(
            slug=cat.get('slug', 'general'),
            voice=CategoryVoiceEnvelope(
                tone=cat.get('voice', {}).get('tone'),
                taboo_words=cat.get('voice', {}).get('vocab_taboo', [])
            )
        ),
        active_digest_item=DigestItemEnvelope(
            item_id=d0.get('id', 'd0') if d0 else 'none',
            title=d0.get('title', '') if d0 else '',
            source=d0.get('source', '') if d0 else '',
            summary=d0.get('summary', '') if d0 else '',
            trial_n=d0.get('trial_n') if d0 else None,
            key_takeaway=d0.get('actionable') if d0 else None
        ) if d0 else None,
        supported_facts=supported_facts,
        conversation_history=[
            TurnHistoryItem(turn=1, role='vera', message=act.body),
            TurnHistoryItem(turn=2, role='merchant', message='Can you share more details?')
        ]
    )
    
    user_prompt = format_user_prompt(envelope, "Can you share more details?", 2)
    
    output_data[cid] = {
        "case_id": cid,
        "category": c["category"],
        "context_density": c["context_density"],
        "raw_merchant": merch,
        "raw_category": cat,
        "raw_trigger": trg,
        "emitted_body": act.body,
        "score_total": score.total,
        "score_spec": score.specificity,
        "score_cat": score.category_fit,
        "score_merch": score.merchant_fit,
        "score_dec": score.decision_quality,
        "score_eng": score.engagement_compulsion,
        "score_penalties": score.penalties,
        "score_hint": score.hint,
        "envelope": envelope.model_dump(),
        "user_prompt": user_prompt
    }

with open(r'c:\projects\magicpin\tests\representative_5_cases_trace.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2)

print("SUCCESS: Wrote tests/representative_5_cases_trace.json")
