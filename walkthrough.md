# Vera AI System: Phase 5C Walkthrough & Verification

## Overview
In **Phase 5C**, we completed the **Sandboxed Sandwich Route Integration** for Vera's `/v1/reply` endpoint. The LLM is integrated strictly as an optional assistive language component within hard deterministic boundaries. Deterministic state machines, context grounding, and multi-tenant safety gates remain the sole decision authority.

---

## 1. Sandwich Route Pipeline

```
                                      POST /v1/reply
                                            │
                                            ▼
                           ┌─────────────────────────────────┐
                           │   1. Contract & Turn Validation │  (Pydantic, Turn Order, Stale/Skipped Turn Check)
                           └────────────────┬────────────────┘
                                            │
                                            ▼
                           ┌─────────────────────────────────┐
                           │ 2. Terminal State Lockout Gate  │  (Barrier 1: If TERMINATED/COMPLETED → action: "end")
                           └────────────────┬────────────────┘
                                            │
                                            ▼
                           ┌─────────────────────────────────┐
                           │   3. Replay Protection Gate     │  (Identical Turn → 200 Cached; Mutated Turn → 409 Conflict)
                           └────────────────┬────────────────┘
                                            │
                                            ▼
                           ┌─────────────────────────────────┐
                           │  4. Deterministic Pre-Gate      │  (Classify Intent: OPT_OUT, REJECT, AUTO_REPLY, OUT_OF_SCOPE,
                           │     & Baseline Composition      │   Direct AFFIRM → 0ms Deterministic Path)
                           └────────────────┬────────────────┘
                                            │
                              [Is Query Nuanced/Ambiguous?]
                                            │
                        ┌───────────────────┴───────────────────┐
                        │ YES                                   │ NO
                        ▼                                       ▼
          ┌───────────────────────────┐            ┌───────────────────────────┐
          │ Build Minimal Envelope    │            │ Deterministic Baseline    │
          │ & Call LLMClient (1500ms) │            │ (Instant 0ms Fallback)    │
          └─────────────┬─────────────┘            └─────────────┬─────────────┘
                        │                                        │
           [LLM Returns Suggestion]                              │
                        │                                        │
                        ▼                                        │
          ┌───────────────────────────┐                          │
          │ 11-Point Output Validator │                          │
          └─────────────┬─────────────┘                          │
                        │                                        │
            ┌───────────┴───────────┐                            │
            │ Valid                 │ Invalid / Timeout / Error  │
            ▼                       ▼                            │
     [Adopt Suggestion]      [Adopt Fallback]                    │
            │                       │                            │
            └───────────┬───────────┘                            │
                        │                                        │
                        ▼                                        ▼
          ┌────────────────────────────────────────────────────────┐
          │       5. Terminal State & Suppression Double Lock      │
          └───────────────────────────┬────────────────────────────┘
                                      │
                                      ▼
          ┌────────────────────────────────────────────────────────┐
          │      6. Deterministic SQLite ACID State Commit         │
          └───────────────────────────┬────────────────────────────┘
                                      │
                                      ▼
                           200 OK (ReplyResponse)
```

---

## 2. Key Architecture Invariants & Boundaries

1. **Deterministic Pre-Gate (`should_use_llm`)**:
   - `OPT_OUT`, `REJECT`, `AUTO_REPLY`, `OUT_OF_SCOPE` (GST, crypto), and direct simple affirmations (`"yes"`, `"ok"`, `"go ahead"`, `"👍"`) bypass the LLM entirely (0 LLM latency, 0 provider cost).
   - Only genuinely nuanced, ambiguous, or clinical questions invoke the LLM.
2. **Context Minimization**:
   - Context is packaged via `build_context_envelope()`, containing only the relevant merchant identity, category voice/taboos, active research digest item, and supported facts.
   - Unrelated merchant/customer records are strictly excluded.
3. **Strict 1.5s Timeout & Circuit Breaker**:
   - Outbound LLM calls are bounded by a hard 1500ms client-side timeout.
   - If the provider encounters 3 consecutive failures, the circuit trips to `OPEN`, immediately serving deterministic responses with 0ms overhead.
4. **11-Point Deterministic Post-Validator (`LLMOutputValidator`)**:
   - Enforces terminal state consistency, action schema correctness, strict supported-fact grounding, category taboo scrubbing, no external action claims (*"prepared/drafted"*, never *"sent/published/scheduled"*), no qualifying language in action mode, CTA compliance, length bounds, and non-empty send bodies.
5. **Terminal State & Suppression Double Lock**:
   - Barrier 1: Fast-exit at turn reception.
   - Barrier 2: Validation check inside `LLMOutputValidator`.
   - Barrier 3: Final state-commit barrier before writing to SQLite.
   - Opt-out triggers persistent composite suppression `("merchant_opt_out", merchant_id)` blocking all future proactive ticks.

---

## 3. Test Suite Verification

### Overall Status: **165 / 165 Tests Passing**

```
============================== test session starts ==============================
rootdir: C:\projects\magicpin
plugins: anyio-4.13.0, asyncio-0.23.8
collected 165 items

tests/test_context.py (7 tests) ........................................ PASSED
tests/test_flow_research_digest.py (12 tests) ........................... PASSED
tests/test_health.py (4 tests) ......................................... PASSED
tests/test_interaction.py (2 tests) .................................... PASSED
tests/test_judge_sim_runner.py (2 tests) ............................... PASSED
tests/test_judge_simulation_gate.py (8 tests) .......................... PASSED
tests/test_llm_client.py (15 tests) .................................... PASSED
tests/test_llm_validator.py (10 tests) ................................. PASSED
tests/test_phase5c_integration.py (17 tests) ........................... PASSED
tests/test_reply_engine.py (88 tests) .................................. PASSED

======================= 165 passed, 1 warning in 30.74s =======================
```

### Official Judge Simulator Scenario Validation:
- **Warmup**: PASSED (`/v1/healthz`, `/v1/metadata`)
- **Context Push**: PASSED (All 5 categories + 5 merchants)
- **Auto-Reply Detection**: PASSED (Turn 1: WAIT 14400s, Turn 2: WAIT 14400s, Turn 3: END)
- **Intent Transition**: PASSED (Switched to ACTION mode with grounded digest content)
- **Hostile Handling**: PASSED (ENDED on hostile message and suppressed)
