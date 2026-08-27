# Vera Phase 7C Targeted Quality Optimization Report

## 1. Comparative Executive Results

| Metric | BASELINE | CONDITIONAL IDENTITY | CONTEXT CTA | SPECIFICITY ENRICHMENT | ALL THREE |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Mean Score** | 35.12 | 35.64 | 34.92 | 36.44 | **37.16** |
| **Median Score** | 36.00 | 36.00 | 34.00 | 38.00 | **36.00** |
| **Min / Max** | 22/41 | 28/43 | 22/45 | 28/46 | **30/46** |
| **Specificity (avg)** | 7.00 | 6.92 | 7.16 | 7.76 | **7.20** |
| **Category Fit (avg)** | 8.48 | 8.52 | 7.88 | 8.40 | **8.76** |
| **Merchant Fit (avg)** | 5.12 | 5.36 | 5.36 | 5.48 | **5.64** |
| **Decision Quality (avg)** | 7.04 | 7.08 | 6.88 | 7.16 | **7.40** |
| **Engagement (avg)** | 7.48 | 7.76 | 7.64 | 7.64 | **8.16** |
| **Penalty Rate** | 0.0% | 0.0% | 0.0% | 0.0% | **0.0%** |

## 2. Category Performance Comparison

| Category | BASELINE | CONDITIONAL IDENTITY | CONTEXT CTA | SPECIFICITY ENRICHMENT | ALL THREE |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Dentists** | 35.43 | 36.00 | 36.71 | 37.71 | **39.00** |
| **Pharmacies** | 34.00 | 33.67 | 31.17 | 35.33 | **34.33** |
| **Physiotherapy** | 37.67 | 39.17 | 36.50 | 39.17 | **40.00** |
| **Salons** | 33.33 | 33.67 | 35.00 | 33.33 | **35.00** |

## 3. Context Density Performance Comparison

| Context Density | BASELINE | CONDITIONAL IDENTITY | CONTEXT CTA | SPECIFICITY ENRICHMENT | ALL THREE |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Medium** | 38.40 | 38.40 | 37.20 | 39.90 | **39.40** |
| **Missing_Optional** | 28.60 | 31.60 | 30.80 | 31.00 | **32.80** |
| **Rich** | 32.17 | 34.33 | 34.50 | 36.33 | **35.50** |
| **Sparse** | 39.50 | 35.75 | 35.00 | 34.75 | **39.50** |

## 4. Regression Analysis

Total Detected Regressions vs Baseline: 35

### 1. Case `qc_0323` (pharmacies, sparse) — Variant `context_cta`
- **Score Impact**: 39 -> 26 (-13 pts)
- **Baseline Body**: `Hi Pharmacies Center team, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — DGCI Circular Apr 2026`
- **Variant Body**: `Hi Pharmacies Center team, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — DGCI Circular Apr 2026`
- **Baseline Breakdown**: Spec:6 Cat:9 Merch:8 Dec:8 Eng:8
- **Variant Breakdown**: Spec:3 Cat:7 Merch:4 Dec:5 Eng:7
- **Judge Hint**: Anchor claims to real, cited sources and weave in merchant‑specific metrics.

### 2. Case `qc_0001` (dentists, medium) — Variant `context_cta`
- **Score Impact**: 41 -> 30 (-11 pts)
- **Baseline Body**: `Hi Sneha, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — JIDA Oct 2026, p.14`
- **Variant Body**: `Hi Sneha, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — JIDA Oct 2026, p.14`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:7 Dec:8 Eng:9
- **Variant Breakdown**: Spec:10 Cat:5 Merch:5 Dec:5 Eng:5
- **Judge Hint**: LLM scoring failed - using basic heuristics

### 3. Case `qc_0211` (pharmacies, medium) — Variant `all_three`
- **Score Impact**: 41 -> 30 (-11 pts)
- **Baseline Body**: `Hi Meera, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — DGCI Circular Apr 2026`
- **Variant Body**: `Hi Meera, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — DGCI Circular Apr 2026`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:8 Dec:8 Eng:8
- **Variant Breakdown**: Spec:5 Cat:8 Merch:4 Dec:6 Eng:7
- **Judge Hint**: Anchor the offer to your footfall stats for sharper relevance.

### 4. Case `qc_0323` (pharmacies, sparse) — Variant `specificity_enrichment`
- **Score Impact**: 39 -> 28 (-11 pts)
- **Baseline Body**: `Hi Pharmacies Center team, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — DGCI Circular Apr 2026`
- **Variant Body**: `Hi Pharmacies Center team, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — DGCI Circular Apr 2026`
- **Baseline Breakdown**: Spec:6 Cat:9 Merch:8 Dec:8 Eng:8
- **Variant Breakdown**: Spec:4 Cat:8 Merch:3 Dec:6 Eng:7
- **Judge Hint**: Anchor the data with a source and a personal touch.

### 5. Case `qc_0183` (physiotherapy, sparse) — Variant `specificity_enrichment`
- **Score Impact**: 40 -> 30 (-10 pts)
- **Baseline Body**: `Hi Arjun, Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed. One item relevant to athletic rehab patients — Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Journal of Orthopaedic & Sports Physical Therapy Jun 2026`
- **Variant Body**: `Hi Arjun, Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed. One item relevant to athletic rehab patients — Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Journal of Orthopaedic & Sports Physical Therapy Jun 2026`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:8 Dec:8 Eng:7
- **Variant Breakdown**: Spec:10 Cat:5 Merch:5 Dec:5 Eng:5
- **Judge Hint**: LLM scoring failed - using basic heuristics

### 6. Case `qc_0239` (physiotherapy, medium) — Variant `context_cta`
- **Score Impact**: 39 -> 29 (-10 pts)
- **Baseline Body**: `Hi Rajan, Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed. One item relevant to athletic rehab patients — Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Journal of Orthopaedic & Sports Physical Therapy Jun 2026`
- **Variant Body**: `Hi Rajan, Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed. One item relevant to athletic rehab patients — Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — Journal of Orthopaedic & Sports Physical Therapy Jun 2026`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:6 Dec:8 Eng:8
- **Variant Breakdown**: Spec:3 Cat:8 Merch:5 Dec:6 Eng:7
- **Judge Hint**: Anchor claims to real sources and weave local context.

### 7. Case `qc_0281` (dentists, sparse) — Variant `context_cta`
- **Score Impact**: 40 -> 30 (-10 pts)
- **Baseline Body**: `Hi Pooja, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — JIDA Oct 2026, p.14`
- **Variant Body**: `Hi Pooja, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — JIDA Oct 2026, p.14`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:7 Dec:8 Eng:8
- **Variant Breakdown**: Spec:10 Cat:5 Merch:5 Dec:5 Eng:5
- **Judge Hint**: LLM scoring failed - using basic heuristics

### 8. Case `qc_0099` (pharmacies, rich) — Variant `context_cta`
- **Score Impact**: 30 -> 22 (-8 pts)
- **Baseline Body**: `Hi Manish, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — DGCI Circular Apr 2026`
- **Variant Body**: `Hi Manish, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — DGCI Circular Apr 2026`
- **Baseline Breakdown**: Spec:4 Cat:8 Merch:5 Dec:6 Eng:7
- **Variant Breakdown**: Spec:2 Cat:6 Merch:4 Dec:4 Eng:6
- **Judge Hint**: Anchor your pitch in the merchant’s own numbers.

### 9. Case `qc_0281` (dentists, sparse) — Variant `conditional_identity`
- **Score Impact**: 40 -> 32 (-8 pts)
- **Baseline Body**: `Hi Pooja, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — JIDA Oct 2026, p.14`
- **Variant Body**: `Dr. Pooja, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — JIDA Oct 2026, p.14`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:7 Dec:8 Eng:8
- **Variant Breakdown**: Spec:6 Cat:9 Merch:3 Dec:6 Eng:8
- **Judge Hint**: Shop name, fact check.

### 10. Case `qc_0351` (physiotherapy, medium) — Variant `context_cta`
- **Score Impact**: 38 -> 30 (-8 pts)
- **Baseline Body**: `Hi Sneha, Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed. One item relevant to athletic rehab patients — Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Journal of Orthopaedic & Sports Physical Therapy Jun 2026`
- **Variant Body**: `Hi Sneha, Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed. One item relevant to athletic rehab patients — Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — Journal of Orthopaedic & Sports Physical Therapy Jun 2026`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:6 Dec:7 Eng:8
- **Variant Breakdown**: Spec:10 Cat:5 Merch:5 Dec:5 Eng:5
- **Judge Hint**: LLM scoring failed - using basic heuristics

### 11. Case `qc_0197` (salons, medium) — Variant `context_cta`
- **Score Impact**: 41 -> 34 (-7 pts)
- **Baseline Body**: `Hi Sunil, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Hair Brand News India Apr 2026`
- **Variant Body**: `Hi Sunil, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — Hair Brand News India Apr 2026`
- **Baseline Breakdown**: Spec:8 Cat:8 Merch:8 Dec:8 Eng:9
- **Variant Breakdown**: Spec:8 Cat:8 Merch:4 Dec:7 Eng:7
- **Judge Hint**: Anchor the content tighter to the merchant’s own context.

### 12. Case `qc_0197` (salons, medium) — Variant `all_three`
- **Score Impact**: 41 -> 34 (-7 pts)
- **Baseline Body**: `Hi Sunil, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Hair Brand News India Apr 2026`
- **Variant Body**: `Hi Sunil, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — Hair Brand News India Apr 2026`
- **Baseline Breakdown**: Spec:8 Cat:8 Merch:8 Dec:8 Eng:9
- **Variant Breakdown**: Spec:8 Cat:8 Merch:3 Dec:7 Eng:8
- **Judge Hint**: Weave in local data and performance stats to boost relevance.

### 13. Case `qc_0197` (salons, medium) — Variant `specificity_enrichment`
- **Score Impact**: 41 -> 35 (-6 pts)
- **Baseline Body**: `Hi Sunil, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Hair Brand News India Apr 2026`
- **Variant Body**: `Hi Sunil, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Hair Brand News India Apr 2026`
- **Baseline Breakdown**: Spec:8 Cat:8 Merch:8 Dec:8 Eng:9
- **Variant Breakdown**: Spec:8 Cat:7 Merch:6 Dec:7 Eng:7
- **Judge Hint**: Blend data with local flavor.

### 14. Case `qc_0043` (pharmacies, rich) — Variant `context_cta`
- **Score Impact**: 33 -> 28 (-5 pts)
- **Baseline Body**: `Hi Tarun, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — DGCI Circular Apr 2026`
- **Variant Body**: `Hi Tarun, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — DGCI Circular Apr 2026`
- **Baseline Breakdown**: Spec:4 Cat:9 Merch:5 Dec:8 Eng:7
- **Variant Breakdown**: Spec:3 Cat:8 Merch:5 Dec:5 Eng:7
- **Judge Hint**: Anchor facts, name the shop, keep the clock ticking.

### 15. Case `qc_0085` (salons, missing_optional) — Variant `context_cta`
- **Score Impact**: 31 -> 27 (-4 pts)
- **Baseline Body**: `Hi there, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Hair Brand News India Apr 2026`
- **Variant Body**: `Hi there, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — Hair Brand News India Apr 2026`
- **Baseline Breakdown**: Spec:8 Cat:7 Merch:2 Dec:6 Eng:8
- **Variant Breakdown**: Spec:8 Cat:6 Merch:0 Dec:6 Eng:7
- **Judge Hint**: Personalize with the salon’s name and a specific offer to boost relevance.

### 16. Case `qc_0169` (dentists, sparse) — Variant `conditional_identity`
- **Score Impact**: 39 -> 35 (-4 pts)
- **Baseline Body**: `Hi Meera, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — JIDA Oct 2026, p.14`
- **Variant Body**: `Dr. Meera, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — JIDA Oct 2026, p.14`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:6 Dec:8 Eng:8
- **Variant Breakdown**: Spec:6 Cat:9 Merch:5 Dec:7 Eng:8
- **Judge Hint**: Embed the shop name and confirm source details to tighten relevance and trust.

### 17. Case `qc_0183` (physiotherapy, sparse) — Variant `conditional_identity`
- **Score Impact**: 40 -> 36 (-4 pts)
- **Baseline Body**: `Hi Arjun, Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed. One item relevant to athletic rehab patients — Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Journal of Orthopaedic & Sports Physical Therapy Jun 2026`
- **Variant Body**: `Dr. Arjun, Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed. One item relevant to athletic rehab patients — Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Journal of Orthopaedic & Sports Physical Therapy Jun 2026`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:8 Dec:8 Eng:7
- **Variant Breakdown**: Spec:5 Cat:9 Merch:7 Dec:7 Eng:8
- **Judge Hint**: Anchor the claim with a clickable reference.

### 18. Case `qc_0211` (pharmacies, medium) — Variant `conditional_identity`
- **Score Impact**: 41 -> 37 (-4 pts)
- **Baseline Body**: `Hi Meera, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — DGCI Circular Apr 2026`
- **Variant Body**: `Hi Meera, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — DGCI Circular Apr 2026`
- **Baseline Breakdown**: Spec:8 Cat:9 Merch:8 Dec:8 Eng:8
- **Variant Breakdown**: Spec:5 Cat:9 Merch:7 Dec:8 Eng:8
- **Judge Hint**: Anchor claims to real sources and weave local performance cues.

### 19. Case `qc_0323` (pharmacies, sparse) — Variant `all_three`
- **Score Impact**: 39 -> 35 (-4 pts)
- **Baseline Body**: `Hi Pharmacies Center team, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — DGCI Circular Apr 2026`
- **Variant Body**: `Hi Pharmacies Center team, DGCI Circular Apr 2026 released. One item relevant to chronic diabetic patients — Wholesale prices on Metformin SR slashed by 22%. Retail margin adjustments recommended (N=1,500). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — DGCI Circular Apr 2026`
- **Baseline Breakdown**: Spec:6 Cat:9 Merch:8 Dec:8 Eng:8
- **Variant Breakdown**: Spec:5 Cat:9 Merch:6 Dec:7 Eng:8
- **Judge Hint**: Anchor the facts to a real source and weave the trigger ID into the hook.

### 20. Case `qc_0197` (salons, medium) — Variant `conditional_identity`
- **Score Impact**: 41 -> 38 (-3 pts)
- **Baseline Body**: `Hi Sunil, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Hair Brand News India Apr 2026`
- **Variant Body**: `Hi Sunil, Hair Brand News India's Apr issue landed. One item relevant to color clients — Pre-treatment bond building reduced chemical breakage by 47% during global smoothening procedures (N=520). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? — Hair Brand News India Apr 2026`
- **Baseline Breakdown**: Spec:8 Cat:8 Merch:8 Dec:8 Eng:9
- **Variant Breakdown**: Spec:8 Cat:8 Merch:6 Dec:8 Eng:8
- **Judge Hint**: Name the shop, not just the owner.

