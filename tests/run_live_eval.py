"""
Live Gemini Evaluation Script for Phase 6.
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import LLM_API_KEY
from app.llm.provider import GeminiProvider
from app.llm.validator import LLMOutputValidator
from tests.evaluate_real_llm import create_evaluation_contexts, TEST_SCENARIOS


async def main():
    key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    if not key:
        print("No GEMINI_API_KEY configured!")
        return

    prov = GeminiProvider(api_key=key, model="gemini-2.5-flash")
    contexts = create_evaluation_contexts()

    print("=" * 80)
    print("LIVE GEMINI 2.5 FLASH EVALUATION RESULTS")
    print("=" * 80)

    for case in TEST_SCENARIOS:
        env = contexts[case["category"]]
        msg = case["input"]
        t0 = time.perf_counter()
        sugg = None
        err = None
        try:
            sugg = await prov.generate(envelope=env, user_message=msg, turn_number=2, timeout_seconds=10.0)
        except Exception as ex:
            err = f"{type(ex).__name__}: {str(ex)[:80]}"

        lat = (time.perf_counter() - t0) * 1000.0

        val = LLMOutputValidator.validate(sugg, env, current_state="AWAITING_REPLY") if sugg else None

        print(f"\n[{case['id']}] Input: {msg}")
        print(f"     Latency: {lat:.1f}ms")
        if sugg:
            print(f"     Suggested Intent: {sugg.suggested_intent} | Proposed Action: {sugg.proposed_action}")
            print(f"     Cited Facts: {sugg.cited_fact_ids} | Unknown Facts: {sugg.unknown_facts_requested}")
            print(f"     Draft Body: {sugg.draft_body}")
            print(f"     Validator Valid: {val.is_valid if val else False} (Errors: {val.error_reasons if val else 'None'})")
            print(f"     Sanitized Body: {val.sanitized_body if val else 'N/A'}")
        else:
            print(f"     Provider failed/returned None: {err}")

        await asyncio.sleep(1.5)  # Rate limit cooldown between API requests


if __name__ == "__main__":
    asyncio.run(main())
