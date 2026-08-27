# Phase 7E: Forensic Review & 60-Case Pipeline Trace Audit

**Audit Date**: 2026-08-27  
**Scope**: Forensic review of `GeneralRelevanceSelector` against the actual current codebase  
**Dataset Evaluated**: 60 in-depth traced cases (20 Original Quality Cases, 20 Unseen Scenarios, 20 Adversarial Cases)  
**Execution Trail**: `RAW CONTEXT` $\rightarrow$ `ATOMIC EXTRACTION` $\rightarrow$ `FEATURE SCORING` $\rightarrow$ `SELECTED / OMITTED FACTS` $\rightarrow$ `LLM ENVELOPE` $\rightarrow$ `RESPONSE` $\rightarrow$ `VALIDATOR` $\rightarrow$ `FINAL OUTPUT`  
**Production Code Status**: 0 lines modified (Pure evidence-driven audit)  

---

## 1. Executive Forensic Summary

| Review Category | Findings / Status | Impact Assessment |
| :--- | :---: | :--- |
| **False Positives (Noise/PII Inclusions)** | **0 / 60 cases (0.0%)** | 100% precision. Zero noise metrics, zero lottery distractions, zero billing leaks. |
| **False Negatives (Vital Context Exclusions)** | **28 / 60 cases (46.7%)** | Two distinct structural failure patterns identified (detailed in Section 3). |
| **Hardcoded Assumptions Identified** | **2 specific heuristics** | Heuristic word list in inbound routing and hardcoded schema path prefixes. |
| **Scoring Weaknesses Identified** | **2 structural issues** | Trigger string fragility and Budget Priority Inversion under rich payloads. |
| **Safety Invariant Verification** | **100% GREEN (208/208 tests)** | Zero safety regressions; opt-out and terminal gates remain 100% authoritative. |

---

## 2. 60-Case Trace Breakdown by Group

### A. Original Benchmark Cases (20 Traced Cases)
- **Cases Audited**: `qc_0001` through `qc_0020` (covering `dentists`, `gyms`, `pharmacies`, `restaurants`, `salons`, `optometrists`, `physiotherapy`, `pet_clinics`).
- **Key Observation**:
  - In `qc_0001` (`research_digest`), the selector successfully extracted and selected `owner_first_name` (*"Sneha"*), `digest[d_dent_01].title`, `trial_n` (*2100*), `summary`, `actionable`, and `customer_aggregate.high_risk_adult_count` (*42*). Score: 5.35 – 5.80.
  - In `qc_0002` through `qc_0020` where `trigger_kind` was named `regulation_change`, `cde_update`, `equipment_update`, or `compliance_alert`, the active digest item was omitted because the scoring engine expected `trigger_kind` to explicitly contain `"digest"` or `"research"`.

### B. Unseen Scenarios (20 Traced Cases)
- **Cases Audited**: `unseen_0001` through `unseen_0020` (covering novel verticals `cardiology`, `dermatology`, `optometry`, `veterinary`, `ayurveda`, `diagnostic_labs`).
- **Key Observation**:
  - In `unseen_0001` (`cardiology`, `research_digest`), the selector generalized cleanly: selected Dr. Aryan's name, `d_card_01` (*"SGLT2 Inhibitor Microvascular Outcomes"*), `trial_n` (*4820*), and actionable recommendations without vertical-specific rules.
  - In `unseen_0013` (`diagnostic_labs`, rich density), **Budget Priority Inversion** occurred: 5 digest facts plus 1 high-risk count pushed Dr. Shalini's `owner_first_name` to rank position #7, dropping it out of the 6-fact envelope.

### C. Adversarial Cases (20 Traced Cases)
- **Cases Audited**: `adv_0001` through `adv_0020` (cross-category injection, $100M lottery noise, commercial sales leakage, overdue arrears, context overload).
- **Key Observation**:
  - `adv_0001` (Cross-category dental crown offer injected into cardiology): **BLOCKED** ($\text{score} = -7.25$, `omitted_context_distraction_risk`).
  - `adv_0002` (Lottery jackpot metric $100M): **BLOCKED** ($\text{score} = -4.20$).
  - `adv_0003` (Sensitive billing arrears & card last4 in patient inquiry): **BLOCKED** ($\text{score} = -9.10$, `omitted_data_sensitivity_policy`).
  - `adv_0004` (Massive 50-metric noise overload): **STRICTLY BUDGET-CAPPED** to $\le 6$ facts.

---

## 3. Forensic Identification of False Negatives & Failure Modes

### Failure Mode 1: Trigger Domain String Fragility (The "Trigger Alias Gap")
- **Mechanism**: In `app/relevance/general_selector.py`, trigger domain detection relies on checking if `trigger_kind` contains specific substring tokens:
  ```python
  is_educational = any(k in trigger_kind for k in ["digest", "research", "clinical", "paper", "study", "guideline"])
  ```
- **Consequence**: When Magicpin passes trigger kinds such as `regulation_change`, `compliance_alert`, `cde_update`, or `equipment_update`, `is_educational` evaluates to `False`. The active digest facts receive generic fallback affinity ($T_f = 0.3$), causing their composite scores to drop to $2.35$ (below the $3.0$ selection threshold).
- **Forensic Diagnosis**: The trigger payload *already explicitly contains* `top_item_id` referencing `category.digest[]`. Checking for the presence of `top_item_id` or `category.digest` is structurally generic and completely eliminates string-matching brittleness.

### Failure Mode 2: Budget Priority Inversion under Rich Envelopes
- **Mechanism**: In rich context scenarios (where a clinical paper has `title`, `summary`, `actionable`, `trial_n`, `patient_segment`, `source`, plus merchant `customer_aggregate`), all 6 facts score between $4.50$ and $5.80$.
- **Consequence**: The clinician's salutation identity (`merchant.identity.owner_first_name`, score $4.45$ or $5.35$) gets pushed to rank #7 or #8, dropping off the envelope budget cap ($N \le 6$).
- **Forensic Diagnosis**: A message without the doctor's name loses personalization points. Salutation identity must have guaranteed priority slotting over secondary metadata (like raw source publication strings).

---

## 4. Audit of Hardcoded Assumptions

| Code Location | Identified Hardcoded Assumption | Risk & Generalization Failure Mode |
| :--- | :--- | :--- |
| `app/relevance/general_selector.py:133` | Substring check on `inbound_query` using hardcoded word list: `["bill", "plan", "pay", "card", "renew", "cancel", "fee"]` | If a merchant asks *"Can you send my monthly invoice?"* or *"What are my subscription charges?"*, the selector treats billing data as unsolicited ($T_f = -0.8$) and omits the invoice info. |
| `app/relevance/general_selector.py:144` | Hardcoded dot-path checks for `"merchant.identity.owner_first_name"` and `"merchant.identity.name"` | If an upstream partner schema sends `merchant.identity.doctor_name` or `merchant.owner_name`, entity affinity scoring fails to recognize it and treats it as a generic string. |
| `app/relevance/general_selector.py:180` | Locality is hardcoded to $G_f = 0.3$ in all educational digests | If Magicpin introduces localized public health alerts (e.g. *"Dengue outbreak in Indiranagar"*), locality remains suppressed unless epidemiological signals are explicitly modeled. |

---

## 5. Scoring Weaknesses & Edge Cases

1. **Path-String Sensitivity**:
   - `path.endswith(".title")` grants $S_f = 0.8$. If a schema uses `headline` or `name` instead of `title`, specificity scoring drops from $0.8$ to $0.0$.
   - *Remedy*: Base specificity scoring on **value data type and string length** ($\text{len}(\text{val}) \ge 10$, $\text{isinstance}(\text{val}, (\text{int}, \text{float}))$) rather than key names.
2. **Dynamic Budget Tie-Breaking**:
   - Currently, Python's `sort(reverse=True)` is stable but does not differentiate between a vital clinician name and a secondary citation string when their scores are equal.
   - *Remedy*: Implement two-tier ranking: Tier 1 (Salutation & Active Trigger Primary Facts) $\rightarrow$ Tier 2 (Supporting Empirical Grounding).

---

## 6. Pre-Implementation Recommendations

Before changing any production code:
1. **Structural Trigger Binding**: Derive trigger domain from payload references (`payload.top_item_id` $\rightarrow$ binds to `category.digest`) rather than checking fragile trigger kind string names.
2. **Value-Driven Specificity**: Score specificity based on data properties (numeric precision, text richness) rather than exact `.title` / `.summary` field suffixes.
3. **Tiered Salience Budgeting**: Ensure the 6-fact envelope always reserves Slot 1 for Salutation/Identity, Slots 2–4 for Primary Trigger Content, and Slots 5–6 for Supporting Cohort/Locality metrics.
