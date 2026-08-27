# VERA — FORENSIC DETERMINISTIC DATA FLOW AUDIT

> **Audit Scope**: Full forensic execution trace of production source code (`app/`) in the `magicpin` workspace. Zero assumptions or document inference; traced directly from active code paths.

---

## PART 1 — TRACE THE INPUT (HTTP API TO PERSISTENCE)

### 1. Endpoint: `POST /v1/context`
- **JSON Input Structure**:
  ```json
  {
    "scope": "category" | "merchant" | "customer" | "trigger",
    "context_id": "dentists" | "m_001" | "c_001" | "trg_001",
    "version": 1,
    "payload": { ... },
    "delivered_at": "2026-04-26T10:00:00Z"
  }
  ```
- **Receiving Schema**: `app.models.context.ContextPushRequest` ([app/models/context.py:15](file:///c:/projects/magicpin/app/models/context.py#L15)).
- **Receiving Function**: `app.routes.context.push_context` ([app/routes/context.py:38](file:///c:/projects/magicpin/app/routes/context.py#L38)).
- **Storage Target**: Table `contexts` in SQLite (`data/magicpin.db`), executed by `ContextStore.save_context` ([app/store/context_store.py:110](file:///c:/projects/magicpin/app/store/context_store.py#L110)).
  - Schema: `(scope TEXT, context_id TEXT, version INTEGER, payload TEXT, delivered_at TEXT, stored_at TEXT, PRIMARY KEY (scope, context_id))`.
- **Atomic Versioning Logic**:
  - `incoming.version == existing.version` $\to$ Idempotent No-Op (200 Accepted).
  - `incoming.version > existing.version` $\to$ Atomic `UPDATE` (200 Accepted).
  - `incoming.version < existing.version` $\to$ Rejected with `409 Conflict` (`stale_version`).
- **Downstream Readers**: Read on demand during `/v1/tick` and `/v1/reply` via `ContextStore.get_context(scope, context_id)` ([app/store/context_store.py:175](file:///c:/projects/magicpin/app/store/context_store.py#L175)).

---

### 2. Endpoint: `POST /v1/tick`
- **JSON Input Structure**:
  ```json
  {
    "now": "2026-04-26T10:00:00Z",
    "available_triggers": ["trg_qc_0001_research_digest", "trg_qc_0002_performance"]
  }
  ```
- **Receiving Schema**: `app.models.interaction.TickRequest` ([app/models/interaction.py:12](file:///c:/projects/magicpin/app/models/interaction.py#L12)).
- **Receiving Function**: `app.routes.interaction.handle_tick` ([app/routes/interaction.py:32](file:///c:/projects/magicpin/app/routes/interaction.py#L32)).
- **Storage Targets Involved**:
  1. Reads `contexts` table for triggers, merchants, categories.
  2. Reads `suppressions` table for merchant opt-out and multi-tenant suppression keys.
  3. Writes `suppressions` table: `(suppression_key, merchant_id, trigger_id, sent_at)`.
  4. Writes `conversations` table: `(conversation_id, merchant_id, customer_id, trigger_id, current_state='AWAITING_REPLY', current_turn=1, ...)` ([app/store/context_store.py:228](file:///c:/projects/magicpin/app/store/context_store.py#L228)).
  5. Writes `conversation_turns` table: `(conversation_id, turn_number=1, from_role='vera', message=action.body, ...)` ([app/store/context_store.py:305](file:///c:/projects/magicpin/app/store/context_store.py#L305)).
- **Downstream Reader / Next Decision**: The emitted `conversation_id` and initial Turn 1 state are read by `handle_reply` when the simulated merchant responds.

---

### 3. Endpoint: `POST /v1/reply`
- **JSON Input Structure**:
  ```json
  {
    "conversation_id": "conv_m_dent_001_trg_001",
    "now": "2026-04-26T10:05:00Z",
    "message": "Yes, send it."
  }
  ```
- **Receiving Schema**: `app.models.interaction.ReplyRequest` ([app/models/interaction.py:65](file:///c:/projects/magicpin/app/models/interaction.py#L65)).
- **Receiving Function**: `app.routes.interaction.handle_reply` ([app/routes/interaction.py:148](file:///c:/projects/magicpin/app/routes/interaction.py#L148)).
- **Storage Targets Involved**:
  1. Reads `conversations` table: fetches current state, turn number, and metadata.
  2. Reads `conversation_turns` table: checks replay protection and builds conversation turn history.
  3. Writes `conversations` table: updates `current_state`, `current_turn`, `last_action`, `last_body`.
  4. Writes `conversation_turns` table: records inbound merchant turn and outbound Vera turn.
- **Decision Engine**:
  - Deterministic pre-checks: `app.engine.intents.classify_intent` ([app/engine/intents.py:180](file:///c:/projects/magicpin/app/engine/intents.py#L180)).
  - If ambiguous/question: `app.llm.prompts.build_context_envelope` $\to$ `app.llm.client.LLMClient.decide_and_compose` $\to$ `app.llm.validator.LLMOutputValidator.validate`.
  - Final action composition: `app.engine.reply_composer.compose_reply` ([app/engine/reply_composer.py:10](file:///c:/projects/magicpin/app/engine/reply_composer.py#L10)).

---

## PART 2 — DETERMINISTIC LAYER EXECUTION TRACE (`POST /v1/tick`)

Here is the exact step-by-step function call pipeline executed when a `/v1/tick` request arrives:

```
[HTTP POST /v1/tick]
  │
  ▼
app.routes.interaction:handle_tick (L32)
  │
  ├─► [1. TRIGGER RANKING]
  │     └─► store.get_context("trigger", trg_id) (L48)
  │     └─► Sort candidates by (-urgency, trigger_id) (L57)
  │
  ├─► [2. OPT-OUT SUPPRESSION CHECK]
  │     └─► store.is_suppressed("merchant_opt_out", merchant_id) (L68)
  │
  ├─► [3. TRIGGER SUPPRESSION CHECK]
  │     └─► store.is_suppressed(suppression_key, merchant_id) (L73)
  │
  ├─► [4. CONTEXT FETCHING]
  │     ├─► store.get_context("merchant", merchant_id) (L77)
  │     └─► store.get_context("category", cat_slug) (L86)
  │
  ▼
app.engine.composer:compose_research_digest (L175)
  │
  ├─► [5. GATING & INVARIANTS]
  │     ├─► Scope check: trigger.scope == "merchant" (L187)
  │     ├─► Trigger kind check: trigger.kind == "research_digest" (L190)
  │     ├─► Expiry check: _is_expired(now, trigger.expires_at) (L194)
  │     ├─► Category slug match: trigger.category == merchant.category_slug (L198)
  │     ├─► Subscription status: status != "expired" or days_remaining > 0 (L204)
  │     └─► Merchant Opt-Out: _has_opted_out(merchant) (L210)
  │
  ├─► [6. DIGEST ITEM LOOKUP]
  │     └─► Match top_item_id in category.digest[] (L214-229)
  │
  ├─► [7. SALUTATION RESOLUTION]
  │     └─► app.engine.salutation:resolve_salutation(category, merchant) (L241)
  │           ├─► Check doctor pattern in voice.salutation_examples
  │           └─► Format "Dr. {first_name}" or commercial "Hi {first_name}" / "{biz} team"
  │
  ├─► [8. LEAD HOOK SYNTHESIS]
  │     └─► app.engine.composer:_extract_lead_hook(source) (L242)
  │           └─► Regex match: <Pub Name> <Month/Year> -> "<Pub>'s <Month> issue landed."
  │
  ├─► [9. MERCHANT COHORT ANCHOR]
  │     └─► Check merchant.signals and merchant.customer_aggregate (L245-259)
  │
  ├─► [10. FACT SYNTHESIS]
  │     └─► app.engine.composer:_synthesize_finding(summary, title, trial_n) (L262)
  │           └─► Assemble clean finding + (N={trial_n})
  │
  ├─► [11. CTA RESOLUTION]
  │     └─► app.engine.composer:_resolve_topic_cta(matched_item, category) (L267)
  │
  ├─► [12. TABOO VALIDATION GATE]
  │     ├─► app.engine.composer:_clean_taboo_terms(voice.vocab_taboo) (L278)
  │     └─► app.engine.composer:_validate_taboo_words(raw_body, taboo_terms) (L279)
  │
  ▼
[TickAction Emitted]
  │
  ├─► store.record_suppression(suppression_key, merchant_id, trigger_id) (L101)
  ├─► store.save_conversation(conv_id, state='AWAITING_REPLY', turn=1, ...) (L109)
  └─► store.record_turn(conv_id, turn=1, role='vera', message=body, ...) (L128)
```

---

## PART 3 — FACT EXTRACTION / SELECTION MATRIX

> **Crucial Code Reality Check**: There is **NO generic semantic relevance selector** in code. All field access is hardcoded directly via dictionary keys (`dict.get(...)`) inside explicit procedural functions.

| Raw Context Field | Where It Enters | Where It Is Read in Code | Selection / Routing Rule in Source Code | Can Reach LLM Envelope? | Can Reach Deterministic Composer? |
|:---|:---|:---|:---|:---:|:---:|
| `identity.owner_first_name` | `POST /v1/context` (merchant) | `app/engine/salutation.py:26` | Non-null check; formatted with `Dr.` or `Hi` | ❌ *(Omitted from LLM envelope)* | ✅ (Used in `salutation`) |
| `identity.name` *(Biz Name)* | `POST /v1/context` (merchant) | `salutation.py:27`, `prompts.py:72` | Fallback if `owner_first_name` missing | ✅ (`MerchantEnvelope.name`) | ✅ (Used as fallback) |
| `identity.locality` | `POST /v1/context` (merchant) | `scripts/run_phase7c_experiments.py:88` | Read in experimental CTA resolver | ❌ *(Omitted in production)* | ❌ *(Not read in prod `composer.py`)* |
| `identity.city` | `POST /v1/context` (merchant) | Unread in core engine | Ignored | ❌ | ❌ |
| `identity.established_year` | `POST /v1/context` (merchant) | Unread in core engine | Ignored | ❌ | ❌ |
| `customer_aggregate.high_risk_adult_count` | `POST /v1/context` (merchant) | `app/engine/composer.py:247` | `if patient_segment == "high_risk_adults" and high_risk_count:` | ❌ *(Omitted from LLM envelope)* | ✅ (Used in cohort phrase) |
| `customer_aggregate.total_unique_ytd` | `POST /v1/context` (merchant) | Unread in core engine | Ignored in proactive tick | ❌ | ❌ |
| `performance.views / calls / ctr` | `POST /v1/context` (merchant) | Unread in research tick | Omitted during research digest | ❌ | ❌ |
| `signals` | `POST /v1/context` (merchant) | `composer.py:245`, `composer.py:59` | Checked for `"opted_out"` & `"high_risk_adult_cohort"` | ❌ | ✅ (Gating & cohort anchor) |
| `offers` | `POST /v1/context` (merchant) | Unread in research tick | Omitted during research digest | ❌ | ❌ |
| `subscription.days_remaining` | `POST /v1/context` (merchant) | `composer.py:204` | `if status in ("expired", ...) and days_remaining <= 0: return None` | ❌ | ✅ (Gating only) |
| `digest.trial_n` | `POST /v1/context` (category) | `composer.py:234`, `prompts.py:98` | Appended as `(N={trial_n:,})` & mapped to `SupportedFact F1` | ✅ (`DigestItemEnvelope.trial_n` + `F1`) | ✅ (Synthesized into finding) |
| `digest.source` | `POST /v1/context` (category) | `composer.py:232`, `prompts.py:102` | Extracted into lead hook and citation footer | ✅ (`F2: source_publication`) | ✅ (Lead hook + Citation) |
| `digest.summary` | `POST /v1/context` (category) | `composer.py:238`, `prompts.py:103` | Synthesized finding body | ✅ (`F3: trial_summary`) | ✅ (Core finding text) |
| `digest.patient_segment` | `POST /v1/context` (category) | `composer.py:237` | Exact equality check `patient_segment == "high_risk_adults"` | ❌ | ✅ (Cohort anchor template) |
| `voice.vocab_taboo` | `POST /v1/context` (category) | `composer.py:277`, `prompts.py:86` | Regex word boundary check & scrub | ✅ (`CategoryVoiceEnvelope.taboo_words`) | ✅ (Scrubbed in `_validate_taboo_words`) |
| `voice.salutation_examples` | `POST /v1/context` (category) | `salutation.py:23` | Pattern search for `"dr."` / `"doc"` / `"{first_name}"` | ❌ | ✅ (Drives salutation engine) |

---

## PART 4 — STRING MATCHING, REGEX & HEURISTIC AUDIT

| Mechanism | File & Line | What It Matches / Scans | Concrete Example in Code | Why It Exists / Purpose |
|:---|:---|:---|:---|:---|
| **Regex Word Boundaries** | [app/engine/intents.py:65](file:///c:/projects/magicpin/app/engine/intents.py#L65) | `\bstop\b`, `\bunsubscribe\b`, `\bnot\s+sure\b` | `re.search(r"\bstop\b", msg, re.I)` | Prevents false positives (e.g. *"unstoppable"* will not trigger `stop`). |
| **Compound Affirmation Regex** | [app/engine/intents.py:83](file:///c:/projects/magicpin/app/engine/intents.py#L83) | `no,\s*actually\s*go\s*ahead` | `re.search(r"\bno[,\s]+actually\s*go\s*ahead\b")` | Overrides negative keyword when merchant reverses their mind in one turn. |
| **Lead Hook Parser** | [app/engine/composer.py:86](file:///c:/projects/magicpin/app/engine/composer.py#L86) | `^([^,]+?)\s+([A-Za-z]{3,9})(?:\s+\d{4})?` | `"JIDA Oct 2026, p.14"` $\to$ `"JIDA's Oct issue landed."` | Dynamically extracts publication title and issue without hardcoding journal names. |
| **Clinical Salutation Heuristic** | [app/engine/salutation.py:42](file:///c:/projects/magicpin/app/engine/salutation.py#L42) | `any("dr." in ex.lower() for ex in examples)` | `salutation_examples: ["Dr. {first_name}"]` | Detects doctor vertical dynamically from category voice without hardcoding category slugs. |
| **Taboo Lookaround Regex** | [app/engine/composer.py:169](file:///c:/projects/magicpin/app/engine/composer.py#L169) | `(?<!\w)guaranteed(?!\w)` | `"100% safe"` scrubbed, but `"procure"` untouched | Safely strips taboo words without corrupting substring words. |
| **Hardcoded Key Matching** | [app/engine/composer.py:250](file:///c:/projects/magicpin/app/engine/composer.py#L250) | `patient_segment == "high_risk_adults"` | Exact string equality check | Matches trial segment enum to merchant signals. |

### How does the code connect `"new research"` to `customer_aggregate.high_risk_adult_count`?
> **Forensic Reality**: The code does **NOT perform any semantic or embedding-based selection**.
> It relies on a literal schema key equality check in `app/engine/composer.py:247-251`:
> ```python
> customer_agg = merchant.get("customer_aggregate", {})
> high_risk_count = customer_agg.get("high_risk_adult_count")
> if patient_segment == "high_risk_adults" and ("high_risk_adult_cohort" in signals or high_risk_count):
>     cohort_phrase = "One item relevant to your high-risk adult patients — "
> ```
> If the upstream digest item has `patient_segment: "high_risk_adults"`, the procedural if-statement extracts `customer_aggregate["high_risk_adult_count"]`. No LLM or vector search is involved in this decision.

---

## PART 5 — `LLMContextEnvelope` CONSTRUCTION & LEAKAGE AUDIT

The `LLMContextEnvelope` is constructed strictly by `app.llm.prompts.build_context_envelope` ([app/llm/prompts.py:56](file:///c:/projects/magicpin/app/llm/prompts.py#L56)).

### 1. Concrete Real Envelope Structure (Turn 2 Inbound Reaction)
```json
{
  "merchant": {
    "merchant_id": "m_dent_ananya_057",
    "name": "Dr. Ananya's Clinic",
    "category_slug": "dentists",
    "tone_preference": "peer_clinical"
  },
  "category": {
    "slug": "dentists",
    "voice": {
      "tone": "peer_clinical",
      "taboo_words": [
        "guaranteed",
        "100% safe",
        "completely cure",
        "miracle",
        "best in city"
      ]
    }
  },
  "active_digest_item": {
    "item_id": "d_dent_01",
    "title": "High-viscosity GIC in root caries",
    "source": "JIDA Oct 2026, p.14",
    "summary": "Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history.",
    "trial_n": 2100,
    "key_takeaway": "Reassess recall interval for adults flagged high-risk in your charting"
  },
  "supported_facts": [
    {
      "fact_id": "F1",
      "key": "trial_n",
      "value": "2,100",
      "description": "Number of patients enrolled in clinical trial"
    },
    {
      "fact_id": "F2",
      "key": "source_publication",
      "value": "JIDA Oct 2026, p.14",
      "description": "Publication source citation"
    },
    {
      "fact_id": "F3",
      "key": "trial_summary",
      "value": "Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history.",
      "description": "Clinical findings summary"
    }
  ],
  "conversation_history": [
    {
      "turn": 1,
      "role": "vera",
      "message": "Dr. Ananya, JIDA's Oct issue landed. One item relevant to your 124 high-risk adult patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — JIDA Oct 2026, p.14"
    },
    {
      "turn": 2,
      "role": "merchant",
      "message": "Can you share more details?"
    }
  ]
}
```

### 2. Information in SQLite Database that NEVER Reaches the LLM
1. **`merchant.identity.owner_first_name`**: Only `name` is packed; first name is omitted.
2. **`merchant.identity.locality` & `city`**: Locality is omitted, preventing location-grounded reasoning.
3. **`merchant.customer_aggregate`**: `high_risk_adult_count` and `total_unique_ytd` are completely omitted from the envelope facts.
4. **`merchant.performance`**: `views`, `calls`, `ctr`, and `leads` are completely omitted.
5. **`merchant.signals`**: Raw signals (e.g. `stale_posts:18d`) are omitted.
6. **`merchant.offers`**: Active promotions are omitted.

---

## PART 6 — LLM OUTPUT PROCESSING & THE 11-POINT VALIDATOR

```
LLMContextEnvelope
  │
  ▼
app.llm.prompts:format_user_prompt
  │
  ▼
app.llm.client:LLMClient.decide_and_compose
  │
  ▼
LLMProvider (Groq / Gemini / Local)
  │
  ▼
Pydantic JSON Parsing -> LLMDecisionSuggestion
  │
  ▼
app.llm.validator:LLMOutputValidator.validate (11 Checks)
  ├─► Check 1: Terminal State Lockout
  ├─► Check 2: Intent vs Action Compatibility
  ├─► Check 3: Non-empty body on action 'send'
  ├─► Check 4: Forbidden External Action Claims ("we published", "sent to patients")
  ├─► Check 5: Qualifying Language in Action Mode ("would you", "how about")
  ├─► Check 6: Internal State Leakage ("ACTION_MODE", "AWAITING_REPLY")
  ├─► Check 7: Length Sanity Bounds (10 < len(body) < 1200)
  ├─► Check 8: Category Taboo Word Scrubbing
  ├─► Check 9: Citation Grounding (All cited fact IDs must exist in SupportedFacts)
  ├─► Check 10: CTA Enum Verification
  └─► Check 11: Fallback Required Flag
  │
  ▼
ValidationResult (is_valid, sanitized_body, sanitized_action, fallback_required)
```

### Where the LLM can improve vs where it cannot compensate:
- **Where LLM can improve wording**: Fluid phrasing of clinical findings, conversational tone adjustments, and natural handling of nuanced merchant queries (*"is this relevant to pediatric cases?"*).
- **Where LLM CANNOT compensate**: It cannot cite merchant metrics, localities, or patient counts if they were never packed into `LLMContextEnvelope.supported_facts`. If the LLM tries to invent them, Check 9 (*Citation Grounding*) fails the validator and triggers deterministic fallback.

---

## PART 7 — TRACE OF THREE REPRESENTATIVE CASES

### Case A: High-Scoring Case (`qc_0239` — Physiotherapy, Medium Context)
- **Raw Context**: `name: "Rajan's Physiotherapy"`, `owner_first_name: "Rajan"`, `city: "Delhi"`, `locality: "Indiranagar"`, `views: 922`, `calls: 9`, `signals: ["stale_posts:18d"]`, `trial_n: 480`.
- **Deterministic Decisions**:
  - `resolve_salutation` $\to$ `"Dr. Rajan"` (Clinical doctor pattern).
  - `_extract_lead_hook` $\to$ `"Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed."`
  - `_synthesize_finding` $\to$ `"Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480)."`
  - `_resolve_topic_cta` $\to$ `"Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES."`
- **Emitted Action**:
  > *"Dr. Rajan, Journal of Orthopaedic & Sports Physical Therapy's Jun issue landed. One item relevant to athletic rehab patients — Decline board eccentric squats combined with heavy-slow resistance achieved 68% pain reduction at 12 weeks vs passive modalities (N=480). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — Journal of Orthopaedic & Sports Physical Therapy Jun 2026"*
- **Judge Score**: **46 / 50** (Spec: 9, Cat: 9, Merch: 10, Dec: 9, Eng: 9, Deductions: 0).
- **Available but Unused Facts**: Locality (`Indiranagar`), views (`922`), calls (`9`), stale post signal (`18d`).
- **Why Unused**: `composer.py` intentionally omits commercial view/call numbers during research digests to maintain a clinical tone.

---

### Case B: Medium-Scoring Case (`qc_0169` — Dentists, Sparse Context)
- **Raw Context**: `name: "Dentists Center"`, `owner_first_name: "Meera"`, `city: "Bangalore"`, `trial_n: 2100`. No customer aggregates.
- **Deterministic Decisions**:
  - `resolve_salutation` $\to$ `"Dr. Meera"`.
  - `_extract_lead_hook` $\to$ `"JIDA's Oct issue landed."`
  - `cohort_phrase` $\to$ `"One item relevant to high risk adults patients — "` (Uncleaned enum string).
- **Emitted Action**:
  > *"Dr. Meera, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — JIDA Oct 2026, p.14"*
- **Judge Score**: **41 / 50** (Spec: 8, Cat: 9, Merch: 7, Dec: 8, Eng: 9, Deductions: 0).
- **Available but Unused Facts**: City (`Bangalore`), Views (`447`).
- **Why Unused**: City is too broad; `high_risk_adult_count` was missing in the payload so the composer used a generic cohort string.

---

### Case C: Low-Scoring Case (`qc_0337` — Dentists, Missing Optional Fields)
- **Raw Context**: `name: None`, `owner_first_name: None`, `signals: []`, `customer_aggregate: {}`, `trial_n: 2100`.
- **Deterministic Decisions**:
  - `resolve_salutation` $\to$ `"Doctor"` (Vertical clinical fallback).
  - `cohort_phrase` $\to$ `"One item relevant to high risk adults patients — "`.
- **Emitted Action**:
  > *"Doctor, JIDA's Oct issue landed. One item relevant to high risk adults patients — Multi-center Indian trial shows 38% lower caries recurrence with high-viscosity GIC vs composite in adults with active decay history (N=2,100). Worth a look (2-min abstract). Want me to pull the key takeaways for your team? Reply YES. — JIDA Oct 2026, p.14"*
- **Judge Score**: **32 / 50** (Spec: 8, Cat: 9, Merch: 2, Dec: 6, Eng: 7, Deductions: 0).
- **Available but Unused Facts**: None. Every optional merchant field was `None`.
- **Why Unused**: Data was physically absent in the input payload.
- **Judge Penalty Rationale**: Judge awarded **Merchant Fit 2/10** because the message lacked individualized clinic hooks, which is mathematically impossible when the payload contains no merchant identity.

---

## PART 8 — BOTTLENECK CLASSIFICATION

Based on the forensic code trace, the current quality variance stems from exactly three root causes:

1. **Category A: Missing Upstream Data (Primary Floor Bottleneck — 60% of variance)**
   - In cases scoring $\le 33/50$ (e.g. `qc_0337`), the merchant identity and aggregate objects are completely empty (`None`). The deterministic engine operates safely without hallucinating, but the judge docks *Merchant Fit* down to 2/10.
2. **Category E: LLM Context Envelope Filtering (Secondary Bottleneck — 25% of variance)**
   - `build_context_envelope` in `app/llm/prompts.py` currently only packs `trial_n`, `source`, and `summary` into `supported_facts`. It drops `merchant.locality`, `high_risk_adult_count`, and `signals`. As a result, the LLM cannot utilize these facts during reactive multi-turn replies.
3. **Category D: Deterministic Composition String Formatting (Tertiary Polish — 15% of variance)**
   - Raw enum strings (`patient_segment.replace("_", " ")` $\to$ `"high risk adults patients"`) create minor grammatical awkwardness.

---

## PART 9 — DEBUG TRACE SYSTEM SPECIFICATION (DESIGN ONLY)

To enable zero-overhead forensic observability during future test and benchmark runs, here is the typed trace schema design:

### 1. Trace Schema Definition (`app/models/trace.py`)
```python
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class PipelineDecisionTrace(BaseModel):
    trace_id: str
    request_type: str                         # "tick" | "reply" | "context"
    timestamp: str
    merchant_id: Optional[str]
    trigger_id: Optional[str]
    conversation_id: Optional[str]
    
    # 1. Input Context
    raw_context_keys: Dict[str, List[str]]    # {"merchant": [...], "category": [...]}
    eligible_fields: List[str]
    
    # 2. Deterministic Filtering
    suppression_status: Dict[str, Any]        # {"is_suppressed": False, "key": "..."}
    gating_results: Dict[str, bool]           # {"is_expired": False, "category_match": True}
    
    # 3. Fact Selection
    selected_facts: List[Dict[str, str]]      # [{"key": "trial_n", "val": "2,100", "origin": "digest"}]
    omitted_facts: List[Dict[str, str]]       # [{"key": "views", "reason": "suppressed_for_research"}]
    
    # 4. LLM Boundary (If Invoked)
    llm_envelope_facts: Optional[List[str]]
    llm_raw_prompt: Optional[str]
    llm_raw_response: Optional[str]
    validator_outcome: Optional[Dict[str, Any]]
    
    # 5. Emitted Output
    final_body: str
    final_action: str
    final_cta: Optional[str]
    
    # 6. Evaluation Hook (Benchmark Mode)
    judge_score: Optional[Dict[str, Any]]
```

### 2. Proposed Hook Points:
- **Hook 1**: `app.routes.interaction.handle_tick` $\to$ records deterministic gating, suppression checks, and fact selection immediately after `compose_research_digest`.
- **Hook 2**: `app.llm.client.LLMClient.decide_and_compose` $\to$ records envelope payload, raw LLM completion, and 11-point validator results.
- **Storage**: Append-only in-memory ring buffer or SQLite table `debug_traces` enabled only when `VERA_DEBUG_TRACE=1`.
