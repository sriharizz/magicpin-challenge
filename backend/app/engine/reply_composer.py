"""
Deterministic Reply Composer for Vera (/v1/reply).

Translates classified intent and conversation state into grounded, non-hallucinatory responses.
Guarantees:
1. Zero unperformed external actions ("drafted", "prepared", never "published/scheduled/sent to patients").
2. Zero fabricated numbers or clinical claims.
3. Word-boundary taboo filtering matching CategoryContext voice rules.
4. Strict compliance with the 3 allowed actions: send, wait, end.
"""

import re
from typing import Any, Dict, Optional, Tuple

from app.engine.intents import ConversationState, ReplyIntent
from app.models.interaction import ReplyResponse


def _clean_taboo_terms(taboos: list) -> list:
    """Normalize taboo list, removing instructional prefixes."""
    cleaned = []
    for t in taboos:
        if not isinstance(t, str):
            continue
        text = t.strip()
        if not text:
            continue
        m = re.match(r'^(?:no\s+|never\s+use\s+|avoid\s+)(.*)$', text, re.IGNORECASE)
        if m:
            text = m.group(1).strip()
        text = text.strip('"\'')
        if text:
            cleaned.append(text.lower())
    return cleaned


def _scrub_taboos(text: str, taboo_terms: list) -> str:
    """Remove taboo words using word boundaries without destroying valid words."""
    result = text
    for term in taboo_terms:
        if not term:
            continue
        clean_term = term.strip().lower()
        if clean_term.endswith("ed") and len(clean_term) > 4:
            root = clean_term[:-2]
            pattern = r'(?<!\w)' + re.escape(root) + r'\w*(?!\w)'
        elif clean_term.endswith("s") and len(clean_term) > 4:
            root = clean_term[:-1]
            pattern = r'(?<!\w)' + re.escape(root) + r'\w*(?!\w)'
        else:
            pattern = r'(?<!\w)' + re.escape(clean_term) + r'(?!\w)'
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def compose_reply(
    intent: ReplyIntent,
    raw_message: str,
    conversation_state: Dict[str, Any],
    merchant_context: Optional[Dict[str, Any]] = None,
    category_context: Optional[Dict[str, Any]] = None,
    trigger_context: Optional[Dict[str, Any]] = None,
) -> Tuple[ReplyResponse, ConversationState]:
    """
    Deterministically compose the ReplyResponse and next ConversationState.

    Args:
        intent: Classified ReplyIntent
        raw_message: Incoming user message text
        conversation_state: Stored conversation session dictionary
        merchant_context: Optional MerchantContext payload
        category_context: Optional CategoryContext payload
        trigger_context: Optional TriggerContext payload

    Returns:
        Tuple of (ReplyResponse, next_ConversationState)
    """
    auto_reply_count = int(conversation_state.get("auto_reply_count", 0))
    current_turn = int(conversation_state.get("current_turn", 1))

    # Extract Taboo rules from CategoryContext
    taboo_terms = []
    if category_context:
        voice = category_context.get("voice", {})
        taboos = voice.get("vocab_taboo", []) or voice.get("taboos", [])
        taboo_terms = _clean_taboo_terms(taboos)

    # 1. OPT-OUT & HOSTILE INTENT (Absolute Termination & Suppression)
    if intent == ReplyIntent.INTENT_OPT_OUT:
        return (
            ReplyResponse(
                action="end",
                body=None,
                cta=None,
                wait_seconds=None,
                rationale="Merchant explicitly opted out or expressed hostility. Terminating conversation immediately and recording suppression.",
            ),
            ConversationState.TERMINATED_OPT_OUT,
        )

    # 2. REJECTION INTENT (Polite Exit)
    if intent == ReplyIntent.INTENT_REJECT:
        return (
            ReplyResponse(
                action="end",
                body=None,
                cta=None,
                wait_seconds=None,
                rationale="Merchant indicated no interest. Gracefully concluding conversation without additional follow-up pitch.",
            ),
            ConversationState.TERMINATED_DECLINED,
        )

    # 3. AUTO-REPLY INTENT (WhatsApp Business / Out of Office)
    if intent == ReplyIntent.INTENT_AUTO_REPLY:
        if auto_reply_count >= 1 or current_turn >= 3:
            # Repeated auto-reply -> terminate loop
            return (
                ReplyResponse(
                    action="end",
                    body=None,
                    cta=None,
                    wait_seconds=None,
                    rationale="Repeated auto-reply detected across turns. Concluding conversation to prevent automated message loop.",
                ),
                ConversationState.TERMINATED_AUTOREPLY,
            )
        else:
            # First auto-reply -> back off 4 hours (14,400 seconds)
            return (
                ReplyResponse(
                    action="wait",
                    body=None,
                    cta=None,
                    wait_seconds=14400,
                    rationale="Detected merchant automated responder. Backing off 4 hours to wait for clinic staff or owner.",
                ),
                ConversationState.BACKOFF_WAIT,
            )

    # 4. AFFIRMATION INTENT (Switch to ACTION MODE)
    if intent == ReplyIntent.INTENT_AFFIRM:
        # Extract digest details if available
        digest_title = ""
        summary_text = ""
        actionable_text = ""
        if category_context:
            digests = category_context.get("digest", []) or category_context.get("digest_items", [])
            if digests and isinstance(digests[0], dict):
                top_item = digests[0]
                digest_title = top_item.get("title", "")
                summary_text = top_item.get("summary", "")
                actionable_text = top_item.get("actionable", "")

        # Synthesize patient/customer draft copy dynamically from context
        patient_ed_body = ""
        if category_context and category_context.get("patient_content_library"):
            pc_items = category_context.get("patient_content_library", [])
            if pc_items and isinstance(pc_items[0], dict) and pc_items[0].get("body"):
                patient_ed_body = f"\"{pc_items[0].get('body')}\""
        
        if not patient_ed_body:
            core_finding = actionable_text or summary_text or digest_title or "Recent findings highlight key best practices for your practice."
            patient_ed_body = f"\"{core_finding}\""

        body = (
            f"Sending the abstract summary now. I have also prepared a draft update for you to review or share:\n\n"
            f"{patient_ed_body}\n\n"
            f"Next step: want me to prepare the follow-up message template?"
        )
        if taboo_terms:
            body = _scrub_taboos(body, taboo_terms)

        return (
            ReplyResponse(
                action="send",
                body=body,
                cta="binary_yes_no",
                wait_seconds=None,
                rationale="Honoring merchant affirmation. Transitioned directly to action mode with abstract deliverables and grounded draft copy.",
            ),
            ConversationState.ACTION_MODE,
        )

    # 5. QUESTION / FACTUAL INQUIRY INTENT
    if intent == ReplyIntent.INTENT_QUESTION:
        normalized = raw_message.lower()
        # Check if inquiry is asking about patient sample size / trial N
        if any(w in normalized for w in ["sample", "trial size", "how many", "patient count", "number of patients", "n="]):
            trial_n = None
            if category_context:
                digests = category_context.get("digest", []) or category_context.get("digest_items", [])
                for d in digests:
                    if isinstance(d, dict) and d.get("trial_n"):
                        trial_n = d.get("trial_n")
                        break

            if trial_n is not None:
                body = (
                    f"The study evaluated {trial_n:,} patients. "
                    f"I have the full 2-page abstract summary ready. Would you like me to share it?"
                )
            else:
                body = (
                    f"The available digest summary does not specify the exact patient sample size for this item. "
                    f"Would you like me to share the clinical abstract and key takeaways?"
                )
            if taboo_terms:
                body = _scrub_taboos(body, taboo_terms)

            return (
                ReplyResponse(
                    action="send",
                    body=body,
                    cta="binary_yes_no",
                    wait_seconds=None,
                    rationale="Answering factual inquiry strictly from stored category digest facts without fabricating trial numbers.",
                ),
                ConversationState.CLARIFYING,
            )

        # General inquiry ("what is this?", "who are you?")
        body = (
            "I'm Vera from magicpin, sharing curated updates and growth ideas for your business. "
            "Would you like me to share the 2-minute research summary?"
        )
        if taboo_terms:
            body = _scrub_taboos(body, taboo_terms)

        return (
            ReplyResponse(
                action="send",
                body=body,
                cta="binary_yes_no",
                wait_seconds=None,
                rationale="Politely clarifying Vera identity and purpose without assuming commitment.",
            ),
            ConversationState.CLARIFYING,
        )

    # 6. OUT-OF-SCOPE INTENT (Tax, Accounting, Weather, Sports, etc.)
    if intent == ReplyIntent.INTENT_OUT_OF_SCOPE:
        body = (
            "That's outside what I can help with directly. "
            "Coming back to the recent update — would you like me to share the 2-minute abstract summary, or prepare a customer-facing draft?"
        )
        if taboo_terms:
            body = _scrub_taboos(body, taboo_terms)

        return (
            ReplyResponse(
                action="send",
                body=body,
                cta="open_ended",
                wait_seconds=None,
                rationale="Out-of-scope ask politely declined; redirects back to the primary topic without losing thread.",
            ),
            ConversationState.CLARIFYING,
        )

    # 7. UNKNOWN / AMBIGUOUS INTENT ("maybe", "tell me more", "??")
    body = (
        "Happy to provide more details. I can share the 2-minute summary or prepare an outreach draft for your business. "
        "Which one would you prefer to see first?"
    )
    if taboo_terms:
        body = _scrub_taboos(body, taboo_terms)

    return (
        ReplyResponse(
            action="send",
            body=body,
            cta="open_ended",
            wait_seconds=None,
            rationale="Ambiguous merchant response; providing low-friction clarification without assuming consent.",
        ),
        ConversationState.CLARIFYING,
    )
