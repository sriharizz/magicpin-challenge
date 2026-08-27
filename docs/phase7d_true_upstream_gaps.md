# Phase 7D — True Upstream Data Gaps Audit

**Audited Cases in Category A**: 95 / 520 (18.3%)

---

## 1. Upstream Data Gap Definition & Verification Rules

A quality deduction is classified as **A — UPSTREAM DATA MISSING** only when:
1. The missing information (e.g. `owner_first_name`, `locality`, `high_risk_adult_count`) was **genuinely absent** from all received scopes (`merchant`, `category`, `trigger`, `customer`).
2. No legitimate proxy existed in any other field without hallucinating.
3. Vera cannot reasonably infer or fabricate the data without violating grounding and truthfulness invariants.

---

## 2. Forensic Evidence Table (Representative Sample)

| Case ID | Category | Context Density | Missing Information | Raw Context Checked | Legitimate Proxy? | Why Vera Cannot Provide It |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `qc_0005` | salons | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0013` | salons | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0015` | physiotherapy | sparse | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0017` | dentists | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0026` | gyms | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0029` | salons | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0035` | pharmacies | sparse | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0040` | pet_care | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0049` | dentists | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0060` | restaurants | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0061` | salons | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0062` | optometry | sparse | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0064` | pet_care | sparse | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0071` | physiotherapy | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0072` | pet_care | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0077` | salons | sparse | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0081` | dentists | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0083` | pharmacies | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0085` | salons | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0090` | gyms | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0093` | salons | sparse | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0095` | physiotherapy | sparse | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0097` | dentists | sparse | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0098` | gyms | sparse | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |
| `qc_0104` | pet_care | missing_optional | `owner_first_name`, `locality` | `merchant.identity`, `merchant.signals` | None | Fabricating a doctor/owner name is a catastrophic hallucination. |

---

## 3. Structural Findings

1. **Synthetic Data Sparsity**: In 100% of sparse and missing_optional test cases, the benchmark dataset explicitly provides empty or minimal `identity` dictionaries `{}`.
2. **Grounding Invariant Maintained**: Vera correctly refuses to guess merchant identities or invent customer counts, choosing conservative greetings (`"Doctor,"` or `"Namaste,"`).
3. **No Hidden Scope Leakage**: Cross-checking `customer`, `category`, and `trigger` confirmed that the missing fields were not present in other scopes.
