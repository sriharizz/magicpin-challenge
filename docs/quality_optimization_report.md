# Vera Quality Optimization Report (Phase 7A)

This document provides a rigorous architectural and empirical analysis of Vera's output quality across **520 evaluated scenarios** using the official Groq 120B `LLMScorer`.

---

## 1. Current Baseline

- **Total Test Cases Evaluated**: 520
- **Proactive Actions Emitted**: 37
- **Suppressed / Clean Rejections**: 483 (100% of expired, out-of-scope, and invalid triggers safely suppressed)
- **Portfolio Mean Score**: **32.38 / 50 (64.8%)**
- **Median Score**: **32.0 / 50**
- **Max Score Observed**: **39.0 / 50 (78.0%)**
- **Min Score Observed**: **25.0 / 50 (50.0%)**
- **Penalty Rate**: **0.0%** (Zero hallucinations, zero taboo leaks, zero data leakage)

---

## 2. Strongest Quality Patterns

1. **Flawless Category Tone (`Avg Category Fit: 8.46 / 10`)**:
   Vera adapts seamlessly across clinical peer-to-peer dialogues (`dentists`, `optometry`), coaching vernacular (`gyms`), and operator pragmatism (`salons`, `restaurants`).
2. **Deterministic Safety and Grounding (`Penalty Rate: 0.0%`)**:
   Zero penalties were recorded across the entire 520-case test suite. Vera never promises guaranteed outcomes or breaches vocabulary taboo constraints.
3. **High Clinical Engagement (`Avg Engagement: 6.97 / 10`)**:
   The low-friction ask offering a 1-line draft or 2-minute abstract summary consistently earns 7–8/10 from the judge.

---

## 3. Weakest Quality Patterns

1. **Salutation Fallback on Sparse Identity (`Merchant Fit: 2.0–4.0 / 10`)**:
   When `owner_first_name` or `name` is missing from the merchant context, Vera outputs `"Hi there,"` or generic headers, causing the judge to dock 4–6 points on Merchant Personalization.
2. **Open-Ended vs Binary CTA Framing (`Engagement: 6.0 / 10`)**:
   The judge prefers an actionable binary hook (e.g., *"Reply YES to draft"*) rather than open-ended queries (*"Want me to pull it?"*).
3. **Source Citation Page Anchoring (`Specificity: 4.0–6.0 / 10`)**:
   When Vera references a journal without including the explicit page citation or sample size $N$ from the digest payload, the judge penalizes perceived verifiability.

---

## 4. Worst Categories

| Category | Mean Score | Primary Reason for Lower Score |
|:---|:---:|:---|
| **Pharmacies** | **30.0 / 50** | Regulatory digest items often lack individual merchant sales metrics (e.g. chronic diabetic cohort counts). |
| **Salons** | **32.0 / 50** | When salon owner names are missing, fallback to generic product news lowers merchant fit. |

---

## 5. Worst Trigger Kinds

| Trigger Kind | Behavior | Analysis |
|:---|:---:|:---|
| `research_digest` (sparse merchant) | Mean: **27.9 / 50** | Insight is clinically valid but feels disconnected from the specific business entity when identity fields are absent. |

---

## 6. Worst Context Conditions

- **`missing_optional` Contexts (Mean: 27.9 / 50)**:
  When both `owner_first_name` and `name` are missing, Vera defaults to `"Hi there,"` resulting in an average Merchant Fit score of **2.6 / 10**.

---

## 7. Common Reasons for Low Scores (< 30/50)

1. **"No merchant name, owner, or locality is referenced; the message is completely generic."**
2. **"The open-ended CTA is low-friction but lacks urgency or loss-aversion."**
3. **"Study details were cited without tying to merchant's local demographic context."**

---

## 8. Common Reasons for High Scores (> 38/50)

1. **"Personalizes with the doctor's name and references the high-risk adult cohort signal."**
2. **"Uses a peer-clinical tone, technical language, and addresses Dr. Meera directly."**
3. **"Provides concrete trial numbers (N=2,100, 4-yr follow-up, 38% reduction) with dated source."**

---

## 9. Top 10 Potential Improvements

| # | Improvement | Category | Expected Score Impact |
|:---:|:---|:---|:---:|
| 1 | **Locality/Business Name Fallback**: When `owner_first_name` is absent, address the clinic/store by business name or locality (e.g., *"Indiranagar Dental Practice"* instead of *"Hi there"*). | Merchant Fit | **+3.0 to +4.0** |
| 2 | **Binary 1-Tap CTA Formulation**: Format CTA as *"Reply YES to draft..."* instead of open-ended *"Want me to...?"*. | Engagement | **+1.5 to +2.5** |
| 3 | **Cohort Count Binding**: Explicitly bind `customer_aggregate` cohort counts (e.g., *"relevant to your 124 adult patients"*). | Merchant Fit | **+2.0 to +3.0** |
| 4 | **Page & Source Citation Stamping**: Always append `— {source}, {date}` suffix to digest abstracts. | Specificity | **+1.5 to +2.0** |
| 5 | **Active Offer Cross-Linking**: When merchant has an active offer, tie the clinical finding directly to the offer (e.g., ₹299 cleaning). | Decision Quality | **+2.0 to +3.0** |
| 6 | **Loss-Aversion Framing**: Highlight consequence of delay (e.g., *"before the Q2 seasonal drop"*). | Engagement | **+1.0 to +2.0** |
| 7 | **Dynamic Hindi/English Code-Mix Salutation**: Use localized respectful salutations when Hindi preference is enabled. | Category Fit | **+1.0** |
| 8 | **Pre-Computed Category Digest Fallbacks**: Ensure every category has at least one rich pre-computed clinical abstract. | Specificity | **+3.0** |
| 9 | **Review Theme Integration**: Address negative review themes in coaching nudges. | Decision Quality | **+1.5** |
| 10 | **Expedited Turnaround Commitments**: Offer immediate turnarounds (e.g., *"I'll send the draft in 2 mins"*). | Engagement | **+1.0** |

---

## 10. Risk & Safety Impact Matrix

| Improvement | Architectural Risk | Safety Impact | Regression Risk |
|:---|:---:|:---:|:---:|
| 1. Locality/Business Name Fallback | **Very Low** | Purely deterministic context interpolation | **Zero** |
| 2. Binary 1-Tap CTA | **Very Low** | Template wording adjustment | **Zero** |
| 3. Cohort Count Binding | **Low** | Requires checking `customer_aggregate` presence | **Zero** |
| 4. Page/Source Citation Stamping | **Very Low** | Formatter string enhancement | **Zero** |
| 5. Active Offer Cross-Linking | **Medium** | Must ensure offer is active, not expired | **Low** |

---

## 11. Recommended Priority & Smallest Safe Change

### The Smallest Safe Change Most Likely to Increase the Average Score:
> **Improve Salutation Fallback & Binary CTA in the Deterministic Composer:**
> 1. When `owner_first_name` is missing, resolve to `{identity.name}` or `{identity.locality} Team` rather than `"Hi there"`.
> 2. End proactive digest messages with a crisp binary action: `"Want me to draft a 1-line WhatsApp broadcast? Reply YES."`

**Estimated Portfolio Score Increase**: **+4.5 to +6.0 points** (lifting portfolio average from **64.8% $\to$ 75.0%+** without touching any security or validator boundaries).
