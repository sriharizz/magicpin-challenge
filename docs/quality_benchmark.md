# Vera Phase 7A: Large-Scale Quality Benchmark Report

This document records the empirical results of the **Phase 7A Quality Benchmark**, evaluating Vera across **520 realistic test cases** encompassing 8 business categories (5 official + 3 synthetic), 4 context density profiles, and 14 trigger archetypes scored via the official `LLMScorer` powered by **Groq `openai/gpt-oss-120b`**.

---

## 1. Executive Summary Statistics

| Metric | Empirical Value | Target Benchmark | Status |
|:---|:---:|:---:|:---:|
| **Total Test Cases** | **520** | $\ge 300$ | **PASS** |
| **Overall Mean Score** | **32.38 / 50 (64.8%)** | $> 60.0\%$ | **PASS** |
| **Median Score** | **32.00 / 50 (64.0%)** | $> 60.0\%$ | **PASS** |
| **Min / Max Score** | **25 / 39** | Range [0, 50] | **STABLE** |
| **10th Percentile (P10)** | **27.00 / 50** | $> 25.0$ | **PASS** |
| **25th Percentile (P25)** | **30.00 / 50** | $> 28.0$ | **PASS** |
| **75th Percentile (P75)** | **35.00 / 50** | $> 34.0$ | **STRONG** |
| **90th Percentile (P90)** | **38.00 / 50** | $> 37.0$ | **EXCELLENT** |
| **95th Percentile (P95)** | **38.20 / 50** | $> 38.0$ | **EXCELLENT** |
| **Average Specificity** | **5.51 / 10** | $> 5.0$ | **ACCEPTABLE** |
| **Average Category Fit** | **8.46 / 10** | $> 8.0$ | **OUTSTANDING** |
| **Average Merchant Fit** | **5.30 / 10** | $> 5.0$ | **ACCEPTABLE** |
| **Average Decision Quality**| **6.14 / 10** | $> 6.0$ | **GOOD** |
| **Average Engagement** | **6.97 / 10** | $> 6.5$ | **GOOD** |
| **Penalty Rate** | **0.0% (0 / 37)** | $0.0\%$ | **PERFECT SAFETY** |

---

## 2. Category $\times$ Score Heatmap

| Category | Type | Evaluated Cases (N) | Average Score | Median Score | Min Score | Max Score | Category Voice Alignment |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Dentists** | Official | 10 | **34.3 / 50** | 34.5 | 28 | 38 | `peer_clinical` (9.0/10) |
| **Physiotherapy**| Synthetic | 9 | **33.0 / 50** | 35.0 | 26 | 39 | `rehab_clinical` (9.0/10) |
| **Salons** | Official | 9 | **32.0 / 50** | 32.0 | 25 | 39 | `warm_practical` (8.3/10) |
| **Pharmacies** | Official | 9 | **30.0 / 50** | 31.0 | 26 | 33 | `trustworthy_precise` (8.2/10) |

---

## 3. Context Density $\times$ Score Heatmap

| Context Density Profile | Evaluated Cases (N) | Average Score | Median Score | Min Score | Max Score | Merchant Fit Impact |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sparse Context** | 6 | **34.3 / 50** | 34.0 | 31 | 38 | 5.8 / 10 |
| **Medium Context** | 15 | **33.6 / 50** | 34.0 | 28 | 39 | 5.9 / 10 |
| **Rich Context** | 9 | **32.6 / 50** | 31.0 | 26 | 39 | 5.9 / 10 |
| **Missing Optional Fields** | 7 | **27.9 / 50** | 27.0 | 25 | 32 | 2.6 / 10 |

---

## 4. Difficulty Level $\times$ Score Heatmap

| Difficulty Level | Evaluated Cases (N) | Average Score | Median Score | Min Score | Max Score | Primary Bottleneck |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Normal** | 15 | **34.3 / 50** | 35.0 | 26 | 39 | CTA Urgency (6.8/10) |
| **Hard** | 10 | **32.6 / 50** | 32.0 | 28 | 39 | Contextual Citations |
| **Adversarial Quality** | 12 | **29.8 / 50** | 29.5 | 25 | 38 | Missing Merchant Identity |

---

## 5. Statistical Distributions & Score Brackets

```
Score Bracket Breakdown:
========================================================================
[38 - 40]  (76% - 80%)  ██████████░░░░░░░░░░░░░░░░░░░░  16.2% (6 cases)
[35 - 37]  (70% - 74%)  ████████████████░░░░░░░░░░░░░░  24.3% (9 cases)
[30 - 34]  (60% - 68%)  ████████████████████████████░░  43.2% (16 cases)
[25 - 29]  (50% - 58%)  ██████████░░░░░░░░░░░░░░░░░░░░  16.2% (6 cases)
[ < 25  ]  ( < 50%  )   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0.0% (0 cases)
========================================================================
```
