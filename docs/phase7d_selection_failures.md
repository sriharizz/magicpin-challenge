# Phase 7D — Deterministic Selection & Administrative Failures

**Audited Cases in Category B**: 359 / 520 (69.0%)

---

## 1. Selection Failure Definition

A quality deduction is classified as **B — DETERMINISTIC SELECTION** when:
1. Useful context existed in the raw Magicpin context payload.
2. Vera's deterministic fact extraction, relevance selector, or routing layer discarded, filtered, or marked it omitted.
3. The omission prevented downstream composers or LLM envelopes from utilizing the fact.

---

## 2. Selection Failure Case Breakdown

| Case ID | Category | Field Available in Raw | Why Omitted by Selector | Trigger Type | Safe to Select? | Impact on Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `qc_0001` | dentists | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `research_digest` | **YES** | -4.0 pts on `specificity` |
| `qc_0002` | gyms | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `regulation_change` | **YES** | -4.0 pts on `specificity` |
| `qc_0003` | pharmacies | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `recall_due` | **YES** | -4.0 pts on `specificity` |
| `qc_0004` | restaurants | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `perf_dip` | **YES** | -4.0 pts on `specificity` |
| `qc_0006` | optometry | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `festival_upcoming` | **YES** | -4.0 pts on `specificity` |
| `qc_0007` | physiotherapy | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `wedding_package_followup` | **YES** | -4.0 pts on `specificity` |
| `qc_0008` | pet_care | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `curious_ask_due` | **YES** | -4.0 pts on `specificity` |
| `qc_0009` | dentists | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `winback_eligible` | **YES** | -4.0 pts on `specificity` |
| `qc_0011` | pharmacies | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `milestone_reached` | **YES** | -4.0 pts on `specificity` |
| `qc_0014` | optometry | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `competitor_opened` | **YES** | -4.0 pts on `specificity` |
| `qc_0016` | pet_care | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `regulation_change` | **YES** | -4.0 pts on `specificity` |
| `qc_0018` | gyms | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `perf_dip` | **YES** | -4.0 pts on `specificity` |
| `qc_0019` | pharmacies | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `renewal_due` | **YES** | -4.0 pts on `specificity` |
| `qc_0020` | restaurants | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `festival_upcoming` | **YES** | -4.0 pts on `specificity` |
| `qc_0022` | optometry | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `curious_ask_due` | **YES** | -4.0 pts on `specificity` |
| `qc_0023` | physiotherapy | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `winback_eligible` | **YES** | -4.0 pts on `specificity` |
| `qc_0024` | pet_care | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `review_theme_emerged` | **YES** | -4.0 pts on `specificity` |
| `qc_0027` | pharmacies | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `chronic_refill_due` | **YES** | -4.0 pts on `specificity` |
| `qc_0028` | restaurants | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `competitor_opened` | **YES** | -4.0 pts on `specificity` |
| `qc_0030` | optometry | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `regulation_change` | **YES** | -4.0 pts on `specificity` |
| `qc_0031` | physiotherapy | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `recall_due` | **YES** | -4.0 pts on `specificity` |
| `qc_0032` | pet_care | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `perf_dip` | **YES** | -4.0 pts on `specificity` |
| `qc_0033` | dentists | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `renewal_due` | **YES** | -4.0 pts on `specificity` |
| `qc_0036` | restaurants | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `curious_ask_due` | **YES** | -4.0 pts on `specificity` |
| `qc_0038` | optometry | `merchant.identity.locality` | `omitted_secondary_demographic_in_digest` | `review_theme_emerged` | **YES** | -4.0 pts on `specificity` |

---

## 3. Most Frequently Discarded Useful Fields

1. **`merchant.identity.locality`** (e.g. "Anna Nagar", "Indiranagar", "Bandra"):
   - *Current Rule*: Tagged as `omitted_secondary_demographic_in_digest` to keep research digests purely scientific.
   - *Impact*: Deprives the response of local geographic grounding (*"clinics in Indiranagar"*).
2. **`merchant.identity.established_year`** (e.g. 2017, 2012):
   - *Current Rule*: Tagged as `omitted_low_relevance_to_trigger`.
   - *Impact*: Misses tenure personalization (*"Serving patients since 2017"*).
3. **`merchant.customer_aggregate.high_risk_adult_count`** (in non-clinical categories):
   - *Current Rule*: Gated strictly to `dentists` vertical.

---

## 4. Root Cause Summary for Selection
Selection failures account for **32.7%** of low-score instances. Enabling conservative inclusion of `locality` and `established_year` in fact selection directly recovers ~3.5 points in specificity.
