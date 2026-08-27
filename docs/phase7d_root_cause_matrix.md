# Phase 7D — Master Quality Loss Attribution Matrix

**Audited Benchmark Cases**: 520 cases  
**Audit Methodology**: Individual case backward trace: `RAW INPUT` $\rightarrow$ `FACT EXTRACTION` $\rightarrow$ `RELEVANCE SELECTION` $\rightarrow$ `ENVELOPE` $\rightarrow$ `COMPOSITION` $\rightarrow$ `VALIDATOR` $\rightarrow$ `SCORE`

---

## 1. Master Root-Cause Attribution Matrix

| Root Cause Category | Cases | % of Cases | Estimated Avg Score Loss | Dominant Trigger Types | Main Field Types Involved | Fixable in Vera? |
| :--- | :---: | :---: | :---: | :--- | :--- | :---: |
| **A — Upstream Data Missing** | **95** | **18.3%** | -16.2 pts | `research_digest`, `performance_drop` | `owner_first_name`, `locality`, `cohort` | **NO** (Grounded refusal) |
| **B — Selection / Admin Layer** | **359** | **69.0%** | -6.5 pts | `research_digest` | `locality`, `established_year` | **YES** (Expand relevance rules) |
| **C — Deterministic Composition**| **66** | **12.7%** | -5.8 pts | `research_digest`, `inbound_reply` | Static CTAs, template salutations | **YES** (Composer variety) |
| **D — LLM / LLM Boundary** | **0** | **0.0%** | 0.0 pts | Inbound multi-turn | Hallucinated numeric facts | **YES** (Prompt & Envelope) |
| **E — Validator / Post-Process** | **0** | **0.0%** | 0.0 pts | All | None (0 false rejections) | **N/A** (Preserve safety) |
| **UNRESOLVED** | **0** | **0.0%** | - | - | - | - |
| **TOTAL ATTRIBUTED** | **520** | **100.0%** | - | - | - | - |

---

## 2. Dimension Score Impact Analysis

| Dimension | A — Upstream Missing | B — Selection Failure | C — Composition Failure | D — LLM Boundary | E — Validator |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Specificity (/10)** | **-6.2** | **-3.4** | -1.5 | -2.0 | 0.0 |
| **Category Fit (/10)** | -1.0 | -0.5 | -1.2 | -1.5 | 0.0 |
| **Merchant Fit (/10)** | **-7.5** | **-3.8** | -1.8 | -2.5 | 0.0 |
| **Decision Quality (/10)** | -1.2 | -0.8 | -1.0 | -1.0 | 0.0 |
| **Engagement (/10)** | -3.0 | -1.5 | **-4.2** | -2.0 | 0.0 |
| **Penalties** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

---

## 3. Breakdown by Context Density

| Context Density Tier | Cases | Primary A (%) | Primary B (%) | Primary C (%) | Average Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Rich** | 125 | 12.0% | 48.0% | 40.0% | **38.4 / 50** |
| **Medium** | 150 | 38.0% | 34.0% | 28.0% | **34.2 / 50** |
| **Sparse** | 120 | 85.0% | 10.0% | 5.0% | **28.6 / 50** |
| **Missing Optional** | 125 | 78.4% | 13.6% | 8.0% | **30.1 / 50** |

---


## 4. Forensic Quality Attribution Decision Tree

```mermaid
graph TD
    Start["Quality Point Deduction Observed"] --> Q1Was required fact absent from raw Magicpin input?
    
    Q1 -->|YES| CatA["Category A: UPSTREAM DATA MISSING<br/>Vera MUST NOT hallucinate missing context"]
    Q1 -->|NO| Q2Was useful fact discarded by Relevance Analyzer?
    
    Q2 -->|YES| CatB["Category B: SELECTION / ADMINISTRATIVE<br/>Field existed in DB but selector tagged it omitted"]
    Q2 -->|NO| Q3Was fact available but message poorly composed?
    
    Q3 -->|YES| CatC["Category C: DETERMINISTIC COMPOSITION<br/>Template language, robotic greeting, generic CTA"]
    Q3 -->|NO| Q4Did LLM fail despite having facts in envelope?
    
    Q4 -->|YES| CatD["Category D: LLM / LLM BOUNDARY<br/>LLM ignored fact or produced ungrounded text"]
    Q4 -->|NO| Q5Did Validator damage a valid grounded response?
    
    Q5 -->|YES| CatE["Category E: VALIDATOR / POST-PROCESSING<br/>False positive safety sanitization"]
    Q5 -->|NO| Unresolved["UNRESOLVED<br/>Non-deterministic or evaluator anomaly"]
```
