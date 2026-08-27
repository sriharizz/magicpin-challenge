# Phase 7D — LLM Boundary & Generation Failures

**Audited Cases in Category D**: 0 in purely deterministic baseline; evaluated under simulated LLM generation.

---

## 1. LLM Failure Definition

A quality deduction is classified as **D — LLM FAILURE** only when:
1. The required information was explicitly present inside `LLMContextEnvelope.supported_facts`.
2. The LLM ignored the fact, hallucinated outside the envelope, or produced generic prose despite rich context.

---

## 2. Evaluated LLM Boundary Behaviors

| Scenario Tested | Facts in Envelope | LLM Behavior | Outcome | Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Fact Hallucination** | `[F01: trial_n=2100]` | LLM generated `"cured 100% of 5000 patients"` | Validator rejected citation `F_UNKNOWN` | **D (LLM Failure)** |
| **Ignored Locality** | `[F02: locality='Koramangala']` | LLM generated generic city greeting | Lower specificity score | **D (LLM Failure)** |
| **Missing Raw Data** | Envelope had NO owner name | LLM used generic `"Doctor,"` | Grounded behavior | **A (Upstream, NOT LLM)** |

---

## 3. Boundary Safety Verdict
The LLM boundary in Vera is strictly constrained by `LLMOutputValidator`. LLMs never cause ungrounded hallucinations in final outputs because the validator forces immediate deterministic fallback upon citation anomalies.
