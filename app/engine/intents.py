"""
Conversation States and Deterministic Intent Classification for Vera.

Enforces:
1. Strict internal state machine
2. Deterministic intent classification with regex word boundaries
3. Robust safety priority:
   QUESTIONING_AFFIRM -> OPT_OUT -> COMPOUND_AFFIRM -> NEGATION_UNCERTAIN -> REJECT -> AUTO_REPLY -> AFFIRM -> QUESTION -> OUT_OF_SCOPE -> UNKNOWN
4. Safe matching:
   - "yes but stop messaging me" -> OPT_OUT
   - "okay, but don't contact me again" -> OPT_OUT
   - "I'm not sure" -> UNKNOWN (never AFFIRM)
   - "sure?" / "yes?" -> QUESTION (never AFFIRM)
   - "no, actually go ahead" -> AFFIRM
   - "do what you think" -> AFFIRM
   - "i am interested" -> AFFIRM
   - "please don't stop" -> UNKNOWN / AFFIRM (bypasses OPT_OUT)
"""

import re
from enum import Enum
from typing import Optional, Tuple


class ConversationState(str, Enum):
    OUTBOUND_SENT = "OUTBOUND_SENT"
    AWAITING_REPLY = "AWAITING_REPLY"
    ACTION_MODE = "ACTION_MODE"
    COMPLETED = "COMPLETED"
    BACKOFF_WAIT = "BACKOFF_WAIT"
    CLARIFYING = "CLARIFYING"
    TERMINATED_AUTOREPLY = "TERMINATED_AUTOREPLY"
    TERMINATED_OPT_OUT = "TERMINATED_OPT_OUT"
    TERMINATED_DECLINED = "TERMINATED_DECLINED"


class ReplyIntent(str, Enum):
    INTENT_AFFIRM = "INTENT_AFFIRM"
    INTENT_REJECT = "INTENT_REJECT"
    INTENT_OPT_OUT = "INTENT_OPT_OUT"
    INTENT_AUTO_REPLY = "INTENT_AUTO_REPLY"
    INTENT_QUESTION = "INTENT_QUESTION"
    INTENT_OUT_OF_SCOPE = "INTENT_OUT_OF_SCOPE"
    INTENT_UNKNOWN = "INTENT_UNKNOWN"


# =============================================================================
# PRE-COMPILED PATTERNS WITH WORD BOUNDARIES (\b)
# =============================================================================

# 1. QUESTIONING AFFIRMATIONS (Doubt / Questioning Consent)
QUESTIONING_AFFIRM_PATTERNS = [
    r"^(?:yes|sure|okay|ok|really)\s*(?:\?+|\.{2,}|\?+!+|!+\?+)\s*$",
    r"\b(?:sure\?|yes\?|okay\?|ok\?|really\?)\b",
]

# 2. "DON'T STOP" NEGATION EXCEPTION PATTERNS (Positive continuation phrases)
DONT_STOP_PATTERNS = [
    r"\b(?:i\s+)?(?:don'?t|do\s+not)\s+want\s+(?:you\s+to\s+)?stop\b",
    r"\b(?:please\s+)?(?:don'?t|do\s+not)\s+stop(?:\s+(?:messaging|contacting|sending))?(?:\s+(?:me|us))?\b",
    r"\bdo\s+not\s+stop\b",
]

# 3. OPT-OUT & HOSTILE PATTERNS (Highest Precedence)
OPT_OUT_PATTERNS = [
    r"\bstop\b",
    r"\bunsubscribe\b",
    r"\bremove\s+me\b",
    r"\b(?:don'?t|do\s+not|never|please\s+don'?t)\s+(?:message|contact|call|text|reach\s+out)\s+(?:me|us)?(?:\s+again)?\b",
    r"\b(?:don'?t|do\s+not)\s+want\s+(?:any|more)?\s*(?:messages?|texts?|calls?|updates?|contact)\b",
    r"\bno\s+more\s+(?:messages?|texts?|calls?|updates?)\b",
    r"\bstop\s+(?:messaging|contacting|texting|calling)\s+(?:me|us)?\b",
    r"\bthis\s+is\s+(?:useless\s+)?spam\b",
    r"\bleave\s+me\s+alone\b",
    r"\bwrong\s+person\b",
    r"\bwrong\s+number\b",
    r"\bopt\s*out\b",
    r"\btake\s+me\s+off\s+(?:the\s+)?list\b",
]

# 4. COMPOUND AFFIRMATIVE OVERRIDES ("no, actually go ahead")
COMPOUND_AFFIRM_PATTERNS = [
    r"\bno[,\s]+(?:actually\s+)?(?:yes[,\s]+)?(?:go\s+ahead|do\s+it|send\s+it|send|proceed|lets?\s+do\s+it)\b",
    r"\bno[,\s]+(?:actually|wait|instead)[,\s]+(?:yes|send|go\s+ahead|proceed|do\s+it)\b",
]

# 5. NEGATION / UNCERTAINTY PATTERNS (Must precede AFFIRM matching to prevent "not sure" -> sure)
NEGATION_UNCERTAIN_PATTERNS = [
    r"\b(?:i'?m\s+|i\s+am\s+)?not\s+sure\b",
    r"\bnot\s+(?:ready|certain|convinced|clear)\b",
    r"\bunclear\b",
    r"\bnever\s+mind\b",
]

# 6. REJECT PATTERNS
REJECT_PATTERNS = [
    r"\bnot\s+interested\b",
    r"\bno\s+thanks?\b",
    r"\bnot\s+now\b",
    r"\bnot\s+right\s+now\b",
    r"\bpass\b",
    r"\bno\b",
    r"\bnope\b",
    r"\bdon'?t\s+want\b",
    r"\bdo\s+not\s+want\b",
    r"\bnot\s+needed\b",
]

# 7. AUTO-REPLY PATTERNS (WhatsApp Business & Out of Office)
AUTO_REPLY_PATTERNS = [
    r"\bthank\s+you\s+for\s+contacting\b",
    r"\bthank\s+you\s+for\s+reaching\s+out\b",
    r"\bwill\s+respond\s+shortly\b",
    r"\bwill\s+get\s+back\s+to\s+you\b",
    r"\bcurrently\s+unavailable\b",
    r"\bauto[- ]generated\b",
    r"\bout\s+of\s+(?:the\s+)?office\b",
    r"\bautomated\s+(?:response|reply|message)\b",
    r"\bour\s+team\s+will\s+respond\b",
    r"\bwe\s+are\s+closed\b",
]

# 8. AFFIRMATION & DELEGATION PATTERNS
# 8. AFFIRMATION & DELEGATION PATTERNS
AFFIRM_PATTERNS = [
    r"\b(?:i'?m\s+|i\s+am\s+)?(?:definitely\s+)?interested\b",
    r"\byes\b",
    r"\byeah\b",
    r"\byep\b",
    r"\bsure\b",
    r"\bokay\b",
    r"\bok\b",
    r"\bokays\b",
    r"\b(?:send|share|draft|prepare|show)\s+(?:it|me|the\s+\w+|details|summary|draft|notes|info)\b",
    r"\bgo\s+ahead\b",
    r"\bdo\s+it\b",
    r"\bproceed\b",
    r"\blets?\s+do\s+it\b",
    r"\bdo\s+whatever\b",
    r"\bdo\s+what\s+you\s+think\b",
    r"\bgo\s+with\s+your\s+recommendation\b",
    r"\byou\s+decide\b",
    r"\buse\s+your\s+judg?ment\b",
    r"\bdo\s+whatever\s+(?:you\s+)?recommend\b",
    r"\bplease\s+do\b",
    r"\bconfirm\b",
    r"\bsounds\s+good\b",
    r"\bworks\s+for\s+me\b",
    r"^👍$",
    r"\b👍\b",
]

# 9. PHRASE-AWARE QUESTION & FACTUAL INQUIRY PATTERNS
QUESTION_PATTERNS = [
    r"^(?:what|how|why|when|who|which)\b",
    r"\bwhat\s+(?:is|are|was|were|about|does|do|can|would)\b",
    r"\bhow\s+(?:many|much|does|do|can|is|are|was)\b",
    r"\bwhy\s+(?:is|are|does|do|did|would)\b",
    r"\bwho\s+(?:is|are|gave|sent)\b",
    r"\bis\s+this\s+(?:free|paid|chargeable)\b",
    r"\bwhat\s+does\s+this\s+mean\b",
    r"\btell\s+me\s+more\b",
    r"\bwho\s+are\s+you\b",
    r"\bsample\s+size\b",
    r"\btrial\s+size\b",
    r"\bpatient\s+count\b",
    r"\bnumber\s+of\s+patients\b",
    r"\bcost\b",
    r"\bprice\b",
    r"\bdosage\b",
    r"\bdetails\b",
    r"\?\s*$",
    r"\?\?+",
]

# 10. OUT-OF-SCOPE PATTERNS (General domain boundaries)
OUT_OF_SCOPE_PATTERNS = [
    r"\b(?:tax|taxes|taxation|filing)\b",
    r"\b(?:accounting|legal\s+advice|lawyer)\b",
    r"\b(?:weather|forecast)\b",
    r"\b(?:crypto|bitcoin|stock\s+market)\b",
    r"\b(?:sports|scores?)\b",
    r"\b(?:loan|banking)\b",
]


def normalize_message(msg: str) -> str:
    """Normalize message text for clean deterministic classification."""
    if not msg:
        return ""
    cleaned = msg.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def classify_intent(message: str) -> Tuple[ReplyIntent, str]:
    """
    Deterministically classify incoming message intent with strict safety precedence:
    1. Questioning Affirmations ("sure?", "yes?") -> INTENT_QUESTION (prevents accidental action mode)
    2. Opt-Out / Hostile (unless "don't stop" exception) -> INTENT_OPT_OUT
    3. Compound Affirmative ("no, actually go ahead") -> INTENT_AFFIRM
    4. Negation Uncertainty ("I'm not sure", "not ready") -> INTENT_UNKNOWN
    5. Rejection ("no", "not interested", "pass") -> INTENT_REJECT
    6. Auto-Reply ("thank you for contacting", "will respond shortly") -> INTENT_AUTO_REPLY
    7. Affirmation ("yes", "interested", "do what you think") -> INTENT_AFFIRM
    8. Question ("how many", "is this free", "?") -> INTENT_QUESTION
    9. Out-of-Scope ("gst", "taxes") -> INTENT_OUT_OF_SCOPE
    10. Fallback -> INTENT_UNKNOWN

    Returns:
        Tuple of (ReplyIntent, normalized_message)
    """
    normalized = normalize_message(message)
    if not normalized:
        return ReplyIntent.INTENT_UNKNOWN, ""

    # Check 1: Questioning Affirmation ("sure?", "yes?", "okay?")
    for pat in QUESTIONING_AFFIRM_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ReplyIntent.INTENT_QUESTION, normalized

    # Check 2: Opt-Out / Hostile (with "don't stop" safeguard)
    is_dont_stop = any(re.search(pat, normalized, re.IGNORECASE) for pat in DONT_STOP_PATTERNS)
    if is_dont_stop:
        return ReplyIntent.INTENT_AFFIRM, normalized

    for pat in OPT_OUT_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ReplyIntent.INTENT_OPT_OUT, normalized

    # Check 3: Compound Affirmative Overrides ("no, actually go ahead")
    for pat in COMPOUND_AFFIRM_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ReplyIntent.INTENT_AFFIRM, normalized

    # Check 4: Negation Uncertainty ("I'm not sure", "not ready", "never mind")
    for pat in NEGATION_UNCERTAIN_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ReplyIntent.INTENT_UNKNOWN, normalized

    # Check 5: Rejection ("not interested", "no thanks", "not now", "no", "pass")
    for pat in REJECT_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ReplyIntent.INTENT_REJECT, normalized

    # Check 6: Auto-Reply ("thank you for contacting", "will respond shortly")
    for pat in AUTO_REPLY_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ReplyIntent.INTENT_AUTO_REPLY, normalized

    # Check 7: Affirmation & Delegation ("yes", "interested", "do what you think", "go ahead")
    for pat in AFFIRM_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ReplyIntent.INTENT_AFFIRM, normalized

    # Check 8: Out-of-Scope ("gst", "tax", "accounting", "crypto")
    for pat in OUT_OF_SCOPE_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ReplyIntent.INTENT_OUT_OF_SCOPE, normalized

    # Check 9: Phrase-Aware Questions ("how many", "what is", "is this free", ends with "?")
    for pat in QUESTION_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ReplyIntent.INTENT_QUESTION, normalized

    # Check 10: Fallback
    return ReplyIntent.INTENT_UNKNOWN, normalized


def should_use_llm(intent: ReplyIntent, raw_message: str) -> bool:
    """
    Deterministic pre-gate determining if an inbound reply requires LLM assistance.

    Returns False for:
    - OPT_OUT, REJECT, AUTO_REPLY (Hard safety fast-exits; 0ms latency, 0 LLM cost)
    - OUT_OF_SCOPE (Standard polite decline)
    - Simple direct affirmations ("yes", "ok", "go ahead", length <= 15 chars)

    Returns True for:
    - INTENT_QUESTION (Nuanced clinical/factual inquiries requiring tailored answers)
    - INTENT_UNKNOWN (Ambiguous, complex, or multi-faceted messages)
    - Long affirmations with custom instructions (length > 15 chars)
    """
    if intent in (
        ReplyIntent.INTENT_OPT_OUT,
        ReplyIntent.INTENT_REJECT,
        ReplyIntent.INTENT_AUTO_REPLY,
        ReplyIntent.INTENT_OUT_OF_SCOPE,
    ):
        return False

    if intent in (ReplyIntent.INTENT_QUESTION, ReplyIntent.INTENT_UNKNOWN):
        return True

    if intent == ReplyIntent.INTENT_AFFIRM:
        clean = normalize_message(raw_message)
        # Direct simple affirmations use fast deterministic path
        if len(clean) <= 15 and clean in (
            "yes",
            "yeah",
            "yep",
            "sure",
            "okay",
            "ok",
            "go ahead",
            "do it",
            "proceed",
            "send it",
            "confirm",
            "👍",
        ):
            return False
        return True

    return False

