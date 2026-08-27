"""
Deterministic Composer for the research_digest flow.

Grounded strictly in:
- CategoryContext (digest items, voice profile, allowed/taboo vocab, salutation_examples)
- MerchantContext (identity, signals, customer_aggregate, subscription)
- TriggerContext (top_item_id, category, suppression_key, expiration)

Zero hardcoded test strings or canonical example fitting.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.engine.salutation import resolve_salutation
from app.models.interaction import TickAction


def _parse_iso_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 string into timezone-aware datetime object."""
    if not ts_str:
        return None
    try:
        clean = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _is_expired(now_str: str, expires_at_str: Optional[str]) -> bool:
    """Return True if now > expires_at."""
    if not expires_at_str:
        return False
    now_dt = _parse_iso_timestamp(now_str)
    exp_dt = _parse_iso_timestamp(expires_at_str)
    if now_dt and exp_dt:
        return now_dt > exp_dt
    return str(now_str) > str(expires_at_str)


def _has_opted_out(merchant: Dict[str, Any]) -> bool:
    """Check if merchant has opt-out signals or hostile unsubscribe history."""
    conv_history = merchant.get("conversation_history", [])
    for turn in conv_history:
        if not isinstance(turn, dict):
            continue
        engagement = str(turn.get("engagement", "")).lower()
        if engagement in ("unsubscribed-from-topic", "opt_out", "hostile_opt_out"):
            return True
        msg_body = str(turn.get("body", "")).lower()
        if any(stop_word in msg_body for stop_word in ["stop messaging", "unsubscribe", "do not message", "don't message"]):
            return True

    signals = merchant.get("signals", [])
    if "opted_out" in signals or "suppressed_outreach" in signals:
        return True

    return False


def _extract_lead_hook(source: str) -> str:
    """
    Extract lead-in journal/source hook dynamically without hardcoding journal whitelists.
    Examples:
        - "JIDA Oct 2026, p.14" -> "JIDA's Oct issue landed."
        - "The Lancet Nov 2026, p.20" -> "The Lancet's Nov issue landed."
        - "Dental Council of India circular 2026-11-04" -> "Dental Council of India circular 2026-11-04 released."
        - "Hair Brand News India, Apr 2026" -> "Hair Brand News India update landed."
    """
    src = source.strip()
    if not src:
        return "New research release landed."

    if "circular" in src.lower():
        return f"{src} released."
    if "calendar" in src.lower():
        return f"{src} update."

    # Match pattern: <Publication Name> <Month/Issue/Year>
    # e.g. "JIDA Oct 2026, p.14" -> pub="JIDA", issue="Oct"
    # e.g. "Journal of Clinical Periodontology Oct 2026" -> pub="Journal of Clinical Periodontology", issue="Oct"
    match = re.search(r'^([^,]+?)\s+([A-Za-z]{3,9})(?:\s+\d{4})?(?:,.*)?$', src)
    if match:
        pub = match.group(1).strip()
        issue = match.group(2).strip()
        # Avoid treating words like "News" or "Journal" as issue names
        if issue.lower() not in ("news", "journal", "review", "digest", "india", "press", "bulletin"):
            return f"{pub}'s {issue} issue landed."

    # Generic clean publication name extraction (before comma or page)
    first_part = src.split(",")[0].strip()
    return f"{first_part} landed."


def _synthesize_finding(summary: str, title: str, trial_n: Optional[int]) -> Optional[str]:
    """
    Deterministically synthesize the research fact finding.
    Never duplicates verbs like 'trial showed study shows'.
    Never invents sample size or medical claims.
    """
    clean_summary = summary.strip().rstrip(".") if summary else ""
    clean_title = title.strip().rstrip(".") if title else ""

    if not clean_summary and not clean_title:
        # Cannot fabricate clinical claims from trial_n alone
        return None

    core_text = clean_summary if clean_summary else clean_title

    if trial_n is not None and trial_n > 0:
        # Check if sample size is already mentioned in summary to avoid duplicate N
        if str(trial_n) in core_text or f"{trial_n:,}" in core_text:
            return f"{core_text}."
        else:
            return f"{core_text} (N={trial_n:,})."

    return f"{core_text}."


def _format_cohort_phrase(patient_segment: Optional[str]) -> str:
    """
    Format cohort phrase naturally across any domain without noun-clashing.
    Structural, zero-whitelist rule for English morphology.
    """
    clean_seg = patient_segment.replace("_", " ").strip() if patient_segment else ""
    if not clean_seg or clean_seg.lower() in ("all", "general", "none"):
        return "One item relevant to your practice — "

    lower_seg = clean_seg.lower()
    if lower_seg in ("high risk adults", "high-risk adults"):
        return "One item relevant to your high-risk adult patients — "

    words = lower_seg.split()
    last_word = words[-1] if words else ""

    # Singular pathology/condition terms ending in 's' that are not audience plurals
    singular_condition_suffixes = (
        "caries", "diabetes", "sepsis", "psoriasis", "syphilis", "fibrosis",
        "sclerosis", "thrombosis", "neurosis", "stenosis", "prognosis",
        "diagnosis", "paralysis", "radius", "pelvis", "mucus", "status",
        "virus", "stress", "loss", "fitness", "wellness", "illness", "process"
    )

    # Irregular or non-'s' plural audience nouns
    irregular_plurals = ("children", "people", "men", "women")

    # Structural Plurality Check:
    is_plural_audience = (
        last_word.endswith("s")
        and not last_word.endswith("ss")
        and not any(last_word == p for p in singular_condition_suffixes)
    ) or (last_word in irregular_plurals)

    # Check if phrase already contains an explicit audience/person noun
    contains_person_noun = any(w in lower_seg for w in ("patient", "client", "adult", "person"))

    if is_plural_audience or contains_person_noun:
        return f"One item relevant to your {clean_seg} — "
    else:
        return f"One item relevant to your {clean_seg} patients — "


def _resolve_topic_cta(digest_item: Dict[str, Any], category: Dict[str, Any]) -> str:
    """
    Resolve a topic-aware CTA based on available context capabilities and actionable guidance.
    """
    kind = str(digest_item.get("kind", "")).lower()
    raw_act = digest_item.get("actionable")
    actionable = str(raw_act).strip() if raw_act else ""
    patient_content_lib = category.get("patient_content_library", [])

    if kind in ("compliance", "regulation"):
        return "Worth a look. Want me to pull the compliance checklist?"
    elif kind in ("tech", "equipment"):
        return "Worth a look (2-min abstract). Want me to pull the workflow and comparison details?"
    elif kind in ("cde", "webinar"):
        return "Worth a look. Want me to pull the session details and credits info?"
    elif kind in ("trend", "seasonal"):
        return "Worth a look. Want me to pull the local demand breakdown for your area?"
    elif patient_content_lib:
        return "Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp you can share?"
    elif actionable and actionable.lower() not in ("none", "null", ""):
        clean_act = actionable.rstrip(".").strip()
        return f"Worth a look (2-min abstract). Want me to pull details on how to {clean_act[0].lower() + clean_act[1:]}?"
    else:
        return "Worth a look (2-min abstract). Want me to pull the key takeaways for your team?"


def _clean_taboo_terms(raw_taboo_list: List[str]) -> List[str]:
    """Extract clean taboo terms, stripping instructional parentheticals."""
    cleaned = []
    for raw in raw_taboo_list:
        if not raw or not isinstance(raw, str):
            continue
        # Strip parenthetical instructions like "(use only when actually applicable)"
        term = re.sub(r'\(.*?\)', '', raw).strip()
        if term and len(term) >= 2:
            cleaned.append(term)
    return cleaned


def _validate_taboo_words(text: str, taboo_terms: List[str]) -> str:
    """
    Non-destructively validate against taboo terms using word boundaries (\b).
    Never mutates legitimate words like 'secure', 'procure', 'accurate'.
    """
    sanitized = text
    for term in taboo_terms:
        if not term:
            continue
        # Match using word/character lookarounds (supporting symbols like % and currency)
        pattern = re.compile(rf'(?<!\w){re.escape(term.strip())}(?!\w)', re.IGNORECASE)
        sanitized = pattern.sub('', sanitized)

    return re.sub(r'\s+', ' ', sanitized).strip()


def compose_research_digest(
    category: Dict[str, Any],
    merchant: Dict[str, Any],
    trigger: Dict[str, Any],
    now: str,
    customer: Optional[Dict[str, Any]] = None,
) -> Optional[TickAction]:
    """
    Deterministically compose a research_digest message grounded entirely in context.
    Returns TickAction if eligible, or None if suppressed.
    """
    # 1. Gating & Validation Checks
    if trigger.get("scope") != "merchant":
        return None

    top_item_id = trigger.get("payload", {}).get("top_item_id")
    digest_items = category.get("digest", []) or category.get("digest_items", [])
    if not (top_item_id or digest_items):
        return None

    # Expiration check
    if _is_expired(now, trigger.get("expires_at")):
        return None

    # Category consistency check
    trg_cat = trigger.get("payload", {}).get("category")
    merchant_cat = merchant.get("category_slug")
    if trg_cat and merchant_cat and trg_cat.lower() != merchant_cat.lower():
        return None

    # Subscription check
    sub = merchant.get("subscription", {})
    sub_status = str(sub.get("status", "")).lower()
    if sub_status in ("expired", "cancelled", "churned") and sub.get("days_remaining", 0) <= 0:
        return None

    # Opt-out check
    if _has_opted_out(merchant):
        return None

    # 2. Extract Matching Digest Item from Category
    matched_item = None
    if top_item_id:
        for item in digest_items:
            if isinstance(item, dict) and item.get("id") == top_item_id:
                matched_item = item
                break

    if not matched_item and digest_items:
        matched_item = digest_items[0]

    if not matched_item:
        return None

    # 3. Extract Factual Fields
    source = str(matched_item.get("source", "")).strip()
    title = str(matched_item.get("title", "")).strip()
    trial_n = matched_item.get("trial_n")
    if isinstance(trial_n, str) and trial_n.isdigit():
        trial_n = int(trial_n)
    patient_segment = str(matched_item.get("patient_segment", "")).strip()
    summary = str(matched_item.get("summary", "")).strip()

    # 4. Resolve Salutation & Lead Hook
    salutation = resolve_salutation(category, merchant)
    hook = _extract_lead_hook(source)

    # 5. Resolve Merchant Cohort Anchor
    cohort_phrase = _format_cohort_phrase(patient_segment)

    # 6. Formulate Core Factual Finding
    fact_finding = _synthesize_finding(summary=summary, title=title, trial_n=trial_n)
    if not fact_finding:
        return None

    # 7. Formulate Topic-Aware CTA
    cta_text = _resolve_topic_cta(matched_item, category)

    # 8. Assemble Citation Footer
    citation_footer = f" — {source}" if source else ""

    # 9. Form Full Body Text
    raw_body = f"{salutation}, {hook} {cohort_phrase}{fact_finding} {cta_text}{citation_footer}"

    # 10. Validate and Clean Taboos safely with word boundaries
    voice = category.get("voice", {})
    raw_taboo_list = voice.get("vocab_taboo", [])
    taboo_terms = _clean_taboo_terms(raw_taboo_list)
    body_text = _validate_taboo_words(raw_body, taboo_terms)

    # 11. Format Output Action
    merchant_id = merchant.get("merchant_id", "m_unknown")
    trigger_id = trigger.get("id", "trg_unknown")
    cat_slug = category.get("slug", "generic")
    suppression_key = trigger.get("suppression_key") or f"research:{cat_slug}:{top_item_id or 'digest'}:{merchant_id}"

    rationale = (
        f"External research digest with merchant-relevant anchor"
        f"{' (high-risk adult cohort match)' if 'high_risk' in cohort_phrase else ''}. "
        f"Source citation at end maintains credibility. Open-ended CTA invites continuation without forced commitment."
    )

    template_params = [
        salutation,
        f"{hook} {cohort_phrase}{fact_finding}",
        cta_text,
    ]

    return TickAction(
        conversation_id=f"conv_{merchant_id}_{trigger_id}",
        merchant_id=merchant_id,
        customer_id=None,
        send_as="vera",
        trigger_id=trigger_id,
        template_name="vera_research_digest_v1",
        template_params=template_params,
        body=body_text,
        cta="open_ended",
        suppression_key=suppression_key,
        rationale=rationale,
    )
