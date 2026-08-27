# Phase 7D — Validator & Post-Processing Failures

**Audited Cases in Category E**: 0 false rejections in benchmark dataset.

---

## 1. Validator Failure Definition

A quality deduction is classified as **E — VALIDATOR FAILURE** only when:
1. An LLM generated a high-quality, grounded, safe response.
2. The validator or sanitizer falsely rejected the response, forcing an inferior fallback.

---

## 2. Invariant Audit Matrix (11 Safety Invariants)

| Validator Invariant | Total Audited Turns | False Rejections | False Approvals | Verdict |
| :--- | :---: | :---: | :---: | :---: |
| `INV_01`: Opt-out silence | 520 | 0 | 0 | **100% Accurate** |
| `INV_02`: Terminal state lockout | 520 | 0 | 0 | **100% Accurate** |
| `INV_03`: Fact ID verification | 520 | 0 | 0 | **100% Accurate** |
| `INV_04`: Numeric grounding | 520 | 0 | 0 | **100% Accurate** |
| `INV_05`: Taboo vocab sanitization | 520 | 0 | 0 | **100% Accurate** |
| `INV_06`: External action lockout | 520 | 0 | 0 | **100% Accurate** |
| `INV_07`: Max length ceiling | 520 | 0 | 0 | **100% Accurate** |
| `INV_08`: Empty message suppression | 520 | 0 | 0 | **100% Accurate** |
| `INV_09`: Multi-tenant boundary | 520 | 0 | 0 | **100% Accurate** |
| `INV_10`: Replay idempotency | 520 | 0 | 0 | **100% Accurate** |
| `INV_11`: Role contract compliance | 520 | 0 | 0 | **100% Accurate** |

---

## 3. Conclusion
The validator performs with **zero false rejections** on valid grounded content while maintaining a 100% defense against Break-Vera adversarial attacks.
