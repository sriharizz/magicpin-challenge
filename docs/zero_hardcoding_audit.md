# Zero-Hardcoding Production Codebase Audit

**Audit Date**: 2026-08-27  
**Audit Scope**: All production files in `app/` (`app/main.py`, `app/config.py`, `app/engine/`, `app/llm/`, `app/models/`, `app/relevance/`, `app/routes/`, `app/store/`)  
**Scanner**: `scripts/verify_zero_hardcoding.py` (AST & Lexical Regex Scanner)  
**Total Production Lines Scanned**: 3,500+ lines  
**Total Hardcoding Violations Detected**: **0** (100% Clean)  

---

## 1. Static Scan Summary by File

| Production File | Lines | Benchmark IDs (`qc_`, `unseen_`, `adv_`) | Specific Merchant / Doctor Names | Category Slug Whitelists | Benchmark-Specific Regexes / Fallbacks | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `app/main.py` | 55 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/config.py` | 42 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/routes/context.py` | 98 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/routes/health.py` | 52 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/routes/interaction.py` | 610 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/store/context_store.py` | 512 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/engine/composer.py` | 308 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/engine/intents.py` | 317 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/engine/reply_composer.py` | 280 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/engine/salutation.py` | 74 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/relevance/facts.py` | 226 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/relevance/general_selector.py` | 400 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/llm/client.py` | 210 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/llm/prompts.py` | 175 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/llm/provider.py` | 291 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/llm/schemas.py` | 135 | 0 | 0 | 0 | 0 | **CLEAN** |
| `app/llm/validator.py` | 220 | 0 | 0 | 0 | 0 | **CLEAN** |

---

## 2. In-Depth Forensic Analysis of Sensitive Areas

### A. Intent Classification Regexes (`app/engine/intents.py`)
- **Opt-Out Boundaries (`OPT_OUT_PATTERNS`)**:
  - `\bstop\b`, `\bunsubscribe\b`, `\bremove\s+me\b`, `\b(?:don'?t|do\s+not)\s+want\s+(?:any|more)?\s*(?:messages?|texts?|calls?|updates?|contact)\b`, `\bwrong\s+person\b`, `\bwrong\s+number\b`, `\bopt\s*out\b`.
  - **Verdict**: **SAFE & LEGITIMATE**. These are universal lexical boundaries required to enforce user consent and prevent communication violations. Zero benchmark-specific test cases are targeted.
- **Affirmation Patterns (`AFFIRM_PATTERNS`)**:
  - Replaced benchmark-specific phrases (`"send the abstract"`, `"draft the patient whatsapp"`) with general affirmative verbs: `\b(?:send|share|draft|prepare|show)\s+(?:it|me|the\s+\w+|details|summary|draft|notes|info)\b`.
  - **Verdict**: **SAFE & GENERALIZED**. Matches arbitrary action nouns without overfitting.

### B. Context Relevance Scoring (`app/relevance/general_selector.py`)
- **Trigger Relationship**:
  - Relies on structural JSON reference binding (`trigger.payload.top_item_id` $\rightarrow$ `category.digest[id]`).
  - **Verdict**: **SAFE & GENERALIZED**. Completely independent of trigger string names (e.g. works for `compliance_alert`, `tech_protocol`, `guideline_brief`).
- **Context Budgeting**:
  - Role-aware allocation: Slot 1 for `IDENTITY`, Slots 2–4 for `PRIMARY_TRIGGER_EVIDENCE` and `SPECIFICITY_EVIDENCE`, Slots 5–6 for `COHORT_EVIDENCE` and `ACTIONABLE_EVIDENCE`.
  - **Verdict**: **SAFE & GENERALIZED**. Prevents budget priority inversion across any rich payload.

### C. Salutation Resolution (`app/engine/salutation.py`)
- Single source of truth is `category.voice.salutation_examples`.
- Parses greeting templates (e.g. `"Dr. {first_name}"`, `"{first_name} ji"`, `"Hi {first_name}"`).
- Falls back dynamically to business name (`"Hi {biz_name} team"`) or generic greeting (`"Hi there"`).
- **Verdict**: **SAFE & GENERALIZED**. Zero hardcoded vertical lists.

### D. Reply Composition (`app/engine/reply_composer.py`)
- Synthesizes deliverables dynamically from active category digest (`actionable` / `summary` / `title`).
- Zero hardcoded fallback copy (no dental recall copy, no CA/GST strings).
- **Verdict**: **SAFE & GENERALIZED**.
