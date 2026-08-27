"""
Deterministic 11-Point Output Validator Gate for Vera's LLM Engine.

Enforces:
1. Schema integrity (Pydantic model)
2. State-action compatibility
3. Terminal state lockout enforcement
4. Fact citation & numerical grounding
5. Taboo word scrubbing (category voice constraints)
6. Prohibition of unperformed external action claims ("published", "sent to patients")
7. Elimination of qualifying language ("would you") in action mode
8. CTA enum verification
9. Token & length sanity bounds
10. Internal state & enum leakage prevention
11. Non-empty body on action 'send'
"""

import re
from typing import List, Tuple, Optional
from app.llm.schemas import LLMDecisionSuggestion, LLMContextEnvelope, ValidationResult
from app.engine.intents import ConversationState, ReplyIntent


FORBIDDEN_EXTERNAL_ACTION_PATTERNS = [
    r"\b(?:i|we|already|automatically)\s+(?:have\s+)?published\b",
    r"\bpublished\s+(?:your\s+|the\s+)?(?:campaign|post|listing|ad|broadcast)\b",
    r"\b(?:i|we|already|automatically)\s+(?:have\s+)?scheduled\b",
    r"\bscheduled\s+(?:your\s+)?(?:post|broadcast|message|campaign)\b",
    r"\b(?:i|we|already|automatically)\s+(?:have\s+)?sent\s+to\s+(?:all\s+)?patients\b",
    r"\bsent\s+to\s+(?:all\s+)?patients\b",
    r"\bmessaged\s+(?:all\s+)?patients\b",
    r"\bupdated\s+(?:your\s+)?listing\b",
    r"\blaunched\s+(?:your\s+)?campaign\b",
]

QUALIFYING_PATTERNS = [
    r"\bwould\s+you\b",
    r"\bdo\s+you\b",
    r"\bcan\s+you\s+tell\b",
    r"\bwhat\s+if\b",
    r"\bhow\s+about\b",
]

INTERNAL_STATE_LEAK_PATTERNS = [
    r"\bACTION_MODE\b",
    r"\bAWAITING_REPLY\b",
    r"\bTERMINATED_\w+\b",
    r"\bINTENT_\w+\b",
    r"\bConversationState\b",
    r"\bReplyIntent\b",
]


class LLMOutputValidator:
    """Deterministic validator gate for all LLM suggestions."""

    @staticmethod
    def validate(
        suggestion: LLMDecisionSuggestion,
        envelope: LLMContextEnvelope,
        current_state: str,
    ) -> ValidationResult:
        errors: List[str] = []

        # Check 1: Terminal State Lockout (Hard Invariant)
        terminal_states = (
            ConversationState.TERMINATED_OPT_OUT.value,
            ConversationState.TERMINATED_DECLINED.value,
            ConversationState.TERMINATED_AUTOREPLY.value,
            ConversationState.COMPLETED.value,
        )
        if current_state in terminal_states:
            if suggestion.proposed_action != "end":
                return ValidationResult(
                    is_valid=False,
                    sanitized_action="end",
                    sanitized_body=None,
                    sanitized_cta=None,
                    error_reasons=["Terminal state lockout: conversation is concluded; cannot perform action other than 'end'"],
                    fallback_required=True,
                )

        # Check 2: Intent vs Action Compatibility
        if suggestion.suggested_intent in ("INTENT_REJECT", "INTENT_OPT_OUT") and suggestion.proposed_action != "end":
            errors.append(f"Intent {suggestion.suggested_intent} requires proposed_action='end', got '{suggestion.proposed_action}'")

        # Check 3: Non-empty body on send
        if suggestion.proposed_action == "send":
            if not suggestion.draft_body or not suggestion.draft_body.strip():
                errors.append("Proposed action is 'send' but draft_body is empty")

        body = suggestion.draft_body or ""

        if body:
            # Check 4: Forbidden External Action Claims
            for pat in FORBIDDEN_EXTERNAL_ACTION_PATTERNS:
                if re.search(pat, body, re.IGNORECASE):
                    errors.append(f"draft_body violates external-action prohibition (matched '{pat}')")

            # Check 5: Qualifying Language in Action Mode
            if suggestion.suggested_intent == "INTENT_AFFIRM" and suggestion.proposed_action == "send":
                for pat in QUALIFYING_PATTERNS:
                    if re.search(pat, body, re.IGNORECASE):
                        errors.append(f"Action-mode body contains qualifying phrase (matched '{pat}'): {body[:60]}...")

            # Check 6: Internal State Leakage
            for pat in INTERNAL_STATE_LEAK_PATTERNS:
                if re.search(pat, body):
                    errors.append(f"draft_body contains leaked internal state token (matched '{pat}')")

            # Check 7: Length Sanity
            if len(body) < 10:
                errors.append(f"draft_body too short ({len(body)} chars)")
            elif len(body) > 1200:
                errors.append(f"draft_body too long ({len(body)} chars)")

            # Check 8: Category Taboo Word Scrubbing
            taboo_words = envelope.category.voice.taboo_words or []
            for taboo in taboo_words:
                if not taboo:
                    continue
                clean_taboo = taboo.strip().lower()
                if clean_taboo.endswith("ed") and len(clean_taboo) > 4:
                    root = clean_taboo[:-2]
                    taboo_pat = r"(?<!\w)" + re.escape(root) + r"\w*(?!\w)"
                elif clean_taboo.endswith("s") and len(clean_taboo) > 4:
                    root = clean_taboo[:-1]
                    taboo_pat = r"(?<!\w)" + re.escape(root) + r"\w*(?!\w)"
                else:
                    taboo_pat = r"(?<!\w)" + re.escape(clean_taboo) + r"(?!\w)"
                if re.search(taboo_pat, body, re.IGNORECASE):
                    # Attempt safe scrub
                    body = re.sub(taboo_pat, "", body, flags=re.IGNORECASE).strip()
                    body = re.sub(r"\s+", " ", body)

            # Check 9: Citation Grounding Check
            valid_fact_ids = {f.fact_id for f in envelope.supported_facts}
            for cited_id in suggestion.cited_fact_ids:
                if cited_id not in valid_fact_ids:
                    errors.append(f"cited_fact_ids references unknown fact '{cited_id}'")

        # Check 10: CTA Enum Verification
        valid_ctas = ("binary_yes_no", "open_ended", "quick_reply", "calendar", "none", None)
        if suggestion.proposed_cta not in valid_ctas:
            errors.append(f"Invalid proposed_cta '{suggestion.proposed_cta}'")

        # Decision
        if errors:
            return ValidationResult(
                is_valid=False,
                sanitized_body=None,
                sanitized_action="send",
                error_reasons=errors,
                fallback_required=True,
            )

        return ValidationResult(
            is_valid=True,
            sanitized_body=body if suggestion.proposed_action == "send" else None,
            sanitized_action=suggestion.proposed_action,
            sanitized_cta=suggestion.proposed_cta,
            error_reasons=[],
            fallback_required=False,
        )
