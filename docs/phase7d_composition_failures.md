# Phase 7D — Deterministic Composition Failures

**Audited Cases in Category C**: 66 / 520 (12.7%)

---

## 1. Composition Failure Definition

A quality deduction is classified as **C — DETERMINISTIC COMPOSITION** when:
1. The necessary facts were available in raw context AND selected by the relevance analyzer.
2. The deterministic response composer generated a message that was robotic, overly repetitive, awkwardly structured, or used a generic CTA.

---

## 2. Forensic Composition Failure Breakdown

| Case ID | Category | Selected Facts Available | Composition Defect | Example Wording in Body | Score Loss |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `qc_0010` | gyms | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0012` | restaurants | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0021` | salons | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0025` | dentists | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0034` | gyms | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0037` | salons | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0048` | pet_care | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0051` | pharmacies | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0066` | gyms | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0082` | gyms | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0084` | restaurants | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0106` | gyms | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0108` | restaurants | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0115` | pharmacies | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0150` | optometry | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0187` | pharmacies | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0194` | gyms | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0214` | optometry | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0215` | physiotherapy | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0232` | pet_care | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0235` | pharmacies | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0238` | optometry | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0240` | pet_care | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0243` | pharmacies | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |
| `qc_0249` | dentists | `digest.title`, `trial_n`, `owner_first_name` | Static Call-to-Action | `"Would you like to review the full paper?"` | -3.5 pts on `engagement` |

---

## 3. Dominant Composition Defects

1. **Static Generic CTA**:
   - `"Would you like to review the full paper?"` repeated across all categories without category-specific nuance.
   - *Fix*: Dynamic conversational CTAs tailored to category tone (e.g. clinical protocols for doctors, client re-booking ideas for salons).
2. **Robotic Fallback Salutation**:
   - When `owner_first_name` is missing, defaulting to `"Doctor,"` rather than dynamic business-name framing (*"To the clinical team at Smile Dental,"*).
3. **Rigid Evidence Sentence Ordering**:
   - Abstract always formatted as: `"[Summary]. ([Source], N=[trial_n])"`.

---

## 4. Remediation Potential
Composition improvements represent the **highest ROI zero-risk enhancement** (+4.5 to +6.0 points on judge score) with 0% risk of safety regressions.
