"""
Prompt Templates and Context Envelope Builders for Vera's LLM Engine (Phase 7F).

Constructs minimal, structure-driven LLMContextEnvelope objects strictly populated
from relevance-selected Fact objects with explicit provenance and Fact IDs.
"""

from typing import Dict, Any, List, Optional
from app.llm.schemas import (
    LLMContextEnvelope,
    MerchantEnvelope,
    CategoryEnvelope,
    CategoryVoiceEnvelope,
    DigestItemEnvelope,
    SupportedFact,
    TurnHistoryItem,
)
from app.relevance.facts import Fact, FactRole
from app.relevance.general_selector import GeneralRelevanceSelector
from app.store.context_store import ContextStore


SYSTEM_PROMPT = """You are Vera's language engine for magicpin proactive merchant engagement.
Your task is to analyze the merchant's message and propose a structured JSON response.

CORE INVARIANTS:
1. GROUNDING:
   - Cite ONLY facts explicitly provided in 'supported_facts' by their 'fact_id' (e.g. ["F1", "F2"]).
   - If the merchant asks for information not in 'supported_facts', list the missing question in 'unknown_facts_requested' and state in draft_body that the current summary does not specify that detail.
   - NEVER invent or hallucinate statistics, trial sizes, sample numbers, or dates.

2. NO EXTERNAL ACTION CLAIMS:
   - Never claim external execution occurred. NEVER say "published", "scheduled", "sent to patients", "updated".
   - Say: "I have prepared", "I can draft", "Here is the draft for you to review", "Sending the abstract now".

3. NO QUALIFYING LANGUAGE IN ACTION MODE:
   - If suggested_intent is INTENT_AFFIRM and proposed_action is 'send', write direct next steps.
   - Example: "Sending the abstract summary now. Here is the draft update: ... Next step: want me to prepare the follow-up message template?"
   - DO NOT use qualifying phrases like "would you", "do you", "can you tell", "what if", "how about".

4. TABOO WORDS:
   - Strictly avoid all words listed in category.voice.taboo_words.

5. OUTPUT FORMAT:
   - Return ONLY a valid JSON object matching the LLMDecisionSuggestion schema:
   {
     "suggested_intent": "INTENT_AFFIRM" | "INTENT_REJECT" | "INTENT_QUESTION" | "INTENT_OUT_OF_SCOPE" | "INTENT_UNKNOWN",
     "confidence": 0.95,
     "proposed_action": "send" | "wait" | "end",
     "response_strategy": "...",
     "draft_body": "...",
     "proposed_cta": "binary_yes_no" | "open_ended" | "quick_reply" | "calendar" | "none",
     "cited_fact_ids": ["F1", ...],
     "unknown_facts_requested": [],
     "rationale": "..."
   }
"""


def build_context_envelope(
    store: ContextStore,
    conversation_id: str,
    merchant_id: str,
    category_slug: Optional[str] = None,
    inbound_query: Optional[str] = None,
    selected_facts: Optional[List[Any]] = None,
) -> LLMContextEnvelope:
    """
    Build a minimal, strictly typed context envelope from persistent SQLite store
    populated directly from relevance-selected facts.
    """
    # 1. Fetch Merchant
    m_ctx = store.get_context("merchant", merchant_id)
    m_payload = m_ctx.get("payload", {}) if m_ctx else {}
    cat_slug = category_slug or m_payload.get("category_slug", "default")

    merchant_env = MerchantEnvelope(
        merchant_id=merchant_id,
        name=m_payload.get("identity", {}).get("name") or m_payload.get("name"),
        category_slug=cat_slug,
        tone_preference=m_payload.get("voice", {}).get("tone"),
    )

    # 2. Fetch Category
    c_ctx = store.get_context("category", cat_slug)
    c_payload = c_ctx.get("payload", {}) if c_ctx else {}
    voice_data = c_payload.get("voice", {})

    category_env = CategoryEnvelope(
        slug=cat_slug,
        voice=CategoryVoiceEnvelope(
            tone=voice_data.get("tone", "peer_clinical"),
            taboo_words=voice_data.get("vocab_taboo", []) or voice_data.get("taboo_words", []),
        ),
    )

    # 3. Select Relevant Facts if not explicitly passed
    facts_to_pack = []
    if selected_facts is not None:
        facts_to_pack = selected_facts
    else:
        # Run general relevance selection
        trace = GeneralRelevanceSelector.select(
            merchant=m_payload,
            category=c_payload,
            inbound_query=inbound_query,
        )
        facts_to_pack = trace.selected_facts

    # 4. Pack Supported Facts Table
    supported_facts: List[SupportedFact] = []
    for idx, f in enumerate(facts_to_pack, start=1):
        f_path = getattr(f, "path", None) or (f.get("path") if isinstance(f, dict) else "")
        f_val = getattr(f, "value", None) if hasattr(f, "value") else (f.get("value") if isinstance(f, dict) else "")
        f_role = getattr(f, "role", None) or (f.get("role") if isinstance(f, dict) else "SUPPORTING")
        if hasattr(f_role, "value"):
            f_role = f_role.value

        supported_facts.append(
            SupportedFact(
                fact_id=f"F{idx}",
                key=f_path,
                value=f"{f_val:,}" if isinstance(f_val, (int, float)) and not isinstance(f_val, bool) else str(f_val),
                description=f"Operational Fact [{f_role}] from {f_path}",
            )
        )

    # 5. Populate Active Digest Item from category if present
    active_digest = None
    digest_list = c_payload.get("digest", []) or c_payload.get("digest_items", [])
    if digest_list and isinstance(digest_list, list):
        top_digest = digest_list[0]
        if isinstance(top_digest, dict):
            trial_n = top_digest.get("trial_n")
            active_digest = DigestItemEnvelope(
                item_id=top_digest.get("id", "d_top"),
                title=top_digest.get("title", ""),
                source=top_digest.get("source", ""),
                summary=top_digest.get("summary", ""),
                trial_n=trial_n,
                key_takeaway=top_digest.get("key_takeaway") or top_digest.get("actionable"),
            )

    # 6. Turn History
    history: List[TurnHistoryItem] = []
    for t_num in range(1, 10):
        turn_data = store.get_turn(conversation_id, t_num)
        if not turn_data:
            break
        msg_text = turn_data.get("message") or turn_data.get("body") or ""
        history.append(
            TurnHistoryItem(
                turn=t_num,
                role=turn_data.get("from_role", "vera"),
                message=msg_text,
            )
        )

    return LLMContextEnvelope(
        merchant=merchant_env,
        category=category_env,
        active_digest_item=active_digest,
        supported_facts=supported_facts,
        conversation_history=history,
    )


def format_user_prompt(envelope: LLMContextEnvelope, inbound_message: str, turn_number: int) -> str:
    """Format user prompt payload with envelope and active inbound message."""
    envelope_json = envelope.model_dump_json(indent=2)
    return (
        f"CONTEXT ENVELOPE:\n{envelope_json}\n\n"
        f"INCOMING MESSAGE (Turn {turn_number}):\n"
        f"From: merchant\n"
        f"Message: \"{inbound_message}\"\n\n"
        f"Analyze this message and respond with the strict LLMDecisionSuggestion JSON."
    )
