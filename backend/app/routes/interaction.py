"""
Interaction Routes (/v1/tick, /v1/reply).

Handles periodic simulated ticks and multi-turn conversation replies.
Phase 3B implements deterministic conversation state management and reply composition.
Instrumented with typed PipelineDecisionTrace for full forensic observability.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
import time
from fastapi import APIRouter, Depends, HTTPException

from app.config import is_debug_trace_enabled
from app.engine.composer import compose_research_digest
from app.engine.intents import ConversationState, ReplyIntent, classify_intent, should_use_llm
from app.engine.reply_composer import compose_reply
from app.llm import get_llm_client, build_context_envelope, LLMOutputValidator
from app.models.interaction import (
    TickAction,
    TickRequest,
    TickResponse,
    ReplyRequest,
    ReplyResponse,
)
from app.models.trace import (
    PipelineDecisionTrace,
    RawInputSummary,
    DeterministicGatingResult,
    FactSelectionTrace,
    LLMBoundaryTrace,
    LLMOutputTrace,
    FinalOutputTrace,
)
from app.relevance.general_selector import GeneralRelevanceSelector
from app.store.context_store import ContextStore, get_context_store

logger = logging.getLogger("vera.interaction")

router = APIRouter(prefix="/v1", tags=["Interaction"])

MAX_ACTIONS_PER_TICK = 20


@router.post("/tick", response_model=TickResponse)
async def handle_tick(
    body: TickRequest,
    store: ContextStore = Depends(get_context_store),
) -> TickResponse:
    """
    Periodic wake-up endpoint called by judge harness.
    Evaluates available triggers against stored contexts and suppression history.
    Enforces deterministic urgency-based ranking and maximum 20 actions per tick.
    Initializes persistent conversation state for every emitted proactive action (Turn 1).
    """
    actions = []

    # 1. Collect and rank candidate triggers
    candidates: List[Tuple[int, str, dict]] = []
    for trg_id in body.available_triggers:
        trg_entity = store.get_context("trigger", trg_id)
        if not trg_entity:
            continue
        trg_payload = trg_entity.get("payload", {})
        urgency = int(trg_payload.get("urgency", 1))
        # Prioritize by highest urgency first, stable trigger ID tiebreaker
        candidates.append((urgency, trg_id, trg_payload))

    # Sort descending by urgency, ascending by trigger ID
    candidates.sort(key=lambda x: (-x[0], x[1]))

    for _, trg_id, trg_payload in candidates:
        if len(actions) >= MAX_ACTIONS_PER_TICK:
            break

        merchant_id = trg_payload.get("merchant_id")
        if not merchant_id:
            continue

        # 2. Check persistent merchant-level opt-out suppression
        if store.is_suppressed("merchant_opt_out", merchant_id):
            if is_debug_trace_enabled():
                trace = PipelineDecisionTrace(
                    trace_id=f"trc_tick_{trg_id}_{merchant_id}",
                    timestamp=body.now,
                    request_type="tick",
                    merchant_id=merchant_id,
                    trigger_id=trg_id,
                    gating=DeterministicGatingResult(
                        has_opted_out=True,
                        gating_passed=False,
                        rejection_reason="merchant_opt_out",
                    ),
                    final_output=FinalOutputTrace(action="suppressed", is_deterministic=True),
                )
                store.save_trace(trace)
            continue

        # 3. Check trigger-level multi-tenant suppression key before composing
        suppression_key = trg_payload.get("suppression_key")
        if suppression_key and store.is_suppressed(suppression_key, merchant_id):
            if is_debug_trace_enabled():
                trace = PipelineDecisionTrace(
                    trace_id=f"trc_tick_{trg_id}_{merchant_id}",
                    timestamp=body.now,
                    request_type="tick",
                    merchant_id=merchant_id,
                    trigger_id=trg_id,
                    gating=DeterministicGatingResult(
                        suppression_status={"suppression_key": suppression_key, "is_suppressed": True},
                        gating_passed=False,
                        rejection_reason="suppression_key_active",
                    ),
                    final_output=FinalOutputTrace(action="suppressed", is_deterministic=True),
                )
                store.save_trace(trace)
            continue

        # 4. Fetch MerchantContext & CategoryContext
        merchant_entity = store.get_context("merchant", merchant_id)
        if not merchant_entity:
            if is_debug_trace_enabled():
                trace = PipelineDecisionTrace(
                    trace_id=f"trc_tick_{trg_id}_{merchant_id}",
                    timestamp=body.now,
                    request_type="tick",
                    merchant_id=merchant_id,
                    trigger_id=trg_id,
                    gating=DeterministicGatingResult(
                        gating_passed=False,
                        rejection_reason="missing_merchant_context",
                    ),
                    final_output=FinalOutputTrace(action="end", is_deterministic=True),
                )
                store.save_trace(trace)
            continue
        merchant_payload = merchant_entity.get("payload", {})

        cat_slug = merchant_payload.get("category_slug")
        cat_entity = store.get_context("category", cat_slug) if cat_slug else None
        cat_payload = cat_entity.get("payload", {}) if cat_entity else {}

        # 6. Deterministic Relevance Analysis
        fact_trace = GeneralRelevanceSelector.select(
            merchant=merchant_payload,
            category=cat_payload,
            trigger=trg_payload,
        )

        # 7. Deterministic Composition
        action = compose_research_digest(
            category=cat_payload,
            merchant=merchant_payload,
            trigger=trg_payload,
            now=body.now,
        )

        if is_debug_trace_enabled():
            trace = PipelineDecisionTrace(
                trace_id=f"trc_tick_{trg_id}_{merchant_id}",
                timestamp=body.now,
                request_type="tick",
                merchant_id=merchant_id,
                trigger_id=trg_id,
                conversation_id=action.conversation_id if action else None,
                raw_input=RawInputSummary(
                    scopes_received=["trigger", "merchant", "category"],
                    available_field_paths=[f.path for f in fact_trace.candidate_facts],
                ),
                gating=DeterministicGatingResult(
                    gating_passed=bool(action is not None),
                    rejection_reason="composition_gated_or_expired" if action is None else None,
                ),
                fact_selection=fact_trace,
                final_output=FinalOutputTrace(
                    action="send" if action else "end",
                    body=action.body if action else None,
                    cta=action.cta if action else None,
                    is_deterministic=True,
                    conversation_id=action.conversation_id if action else None,
                ),
            )
            store.save_trace(trace)

        if action:
            # Record suppression key for this specific merchant
            store.record_suppression(
                suppression_key=action.suppression_key,
                merchant_id=action.merchant_id,
                trigger_id=action.trigger_id,
                sent_at=body.now,
            )

            # Persist Conversation State (Turn 1: Proactive Outbound)
            store.save_conversation(
                conversation_id=action.conversation_id,
                merchant_id=action.merchant_id,
                customer_id=action.customer_id,
                trigger_id=action.trigger_id,
                suppression_key=action.suppression_key,
                category_slug=cat_slug,
                current_state=ConversationState.AWAITING_REPLY.value,
                current_turn=1,
                auto_reply_count=0,
                last_action="send",
                last_body=action.body,
                last_rationale=action.rationale,
                last_cta=action.cta,
                last_wait_seconds=None,
                created_at=body.now,
            )

            # Record Turn 1 in conversation_turns
            store.record_turn(
                conversation_id=action.conversation_id,
                turn_number=1,
                from_role="vera",
                message=action.body,
                intent="PROACTIVE_TICK",
                state_after=ConversationState.AWAITING_REPLY.value,
                action="send",
                body=action.body,
                rationale=action.rationale,
                cta=action.cta,
                wait_seconds=None,
                timestamp=body.now,
            )

            actions.append(action)

    return TickResponse(actions=actions)


@router.post("/reply", response_model=ReplyResponse)
async def handle_reply(
    body: ReplyRequest,
    store: ContextStore = Depends(get_context_store),
) -> ReplyResponse:
    """
    Conversation reply endpoint called by judge harness with simulated responses.
    Phase 3B implements deterministic conversation state management, intent routing,
    turn replay protection, and persistent suppression tracking.
    """
    # 1. Request Contract Validation
    if not body.conversation_id or not body.conversation_id.strip():
        raise HTTPException(status_code=400, detail="conversation_id cannot be empty")

    if body.from_role not in ("merchant", "customer"):
        raise HTTPException(status_code=400, detail="from_role must be 'merchant' or 'customer'")

    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    if body.turn_number < 1:
        raise HTTPException(status_code=400, detail="turn_number must be >= 1")

    # 2. Session Context Retrieval & On-the-fly Initialization
    conv = store.get_conversation(body.conversation_id)

    if conv is None:
        # Gracefully initialize session on the fly (supports isolation test harnesses & judge simulator)
        merchant_id = body.merchant_id
        if not merchant_id:
            # Fallback to first available merchant if not provided
            merchants = store.list_contexts_by_scope("merchant")
            merchant_id = merchants[0]["context_id"] if merchants else "m_default"

        # Lookup category_slug from merchant if available
        m_entity = store.get_context("merchant", merchant_id)
        cat_slug = m_entity.get("payload", {}).get("category_slug") if m_entity else None

        initial_turn = body.turn_number - 1 if body.turn_number > 1 else 1
        store.save_conversation(
            conversation_id=body.conversation_id,
            merchant_id=merchant_id,
            customer_id=body.customer_id,
            trigger_id=None,
            suppression_key=None,
            category_slug=cat_slug,
            current_state=ConversationState.AWAITING_REPLY.value,
            current_turn=initial_turn,
            auto_reply_count=0,
            last_action=None,
            created_at=body.received_at,
        )
        conv = store.get_conversation(body.conversation_id)

    # 3. Terminal State Lockout (CRITICAL INVARIANT: Never process or send on concluded thread)
    if conv.get("current_state") in (
        ConversationState.TERMINATED_OPT_OUT.value,
        ConversationState.TERMINATED_DECLINED.value,
        ConversationState.TERMINATED_AUTOREPLY.value,
        ConversationState.COMPLETED.value,
    ):
        if is_debug_trace_enabled():
            trace = PipelineDecisionTrace(
                trace_id=f"trc_reply_{body.conversation_id}_t{body.turn_number}",
                timestamp=body.received_at,
                request_type="reply",
                merchant_id=conv.get("merchant_id"),
                conversation_id=body.conversation_id,
                gating=DeterministicGatingResult(
                    is_terminal=True,
                    gating_passed=False,
                    rejection_reason="terminal_state_lockout",
                ),
                final_output=FinalOutputTrace(
                    action="end",
                    body=None,
                    cta=None,
                    is_deterministic=True,
                    conversation_id=body.conversation_id,
                ),
            )
            store.save_trace(trace)

        return ReplyResponse(
            action="end",
            body=None,
            cta=None,
            wait_seconds=None,
            rationale="Conversation is already concluded on this thread. No further actions permitted.",
        )

    # 4. Merchant ID Verification (if both provided)
    if body.merchant_id and conv.get("merchant_id") and conv["merchant_id"] != body.merchant_id:
        raise HTTPException(status_code=400, detail="merchant_id does not match existing conversation record")

    stored_turn = int(conv.get("current_turn", 1))

    # 5. Turn Order & Idempotent Replay Protection
    # Case A: Duplicate Turn Replay (Exact same turn number requested again)
    if body.turn_number == stored_turn:
        last_turn = store.get_turn(body.conversation_id, body.turn_number)
        if last_turn:
            # Check message payload consistency
            if body.message.strip().lower() == str(last_turn.get("message", "")).strip().lower():
                return ReplyResponse(
                    action=last_turn["action"],
                    body=last_turn["body"],
                    cta=last_turn["cta"],
                    wait_seconds=last_turn["wait_seconds"],
                    rationale=f"[Idempotent replay] {last_turn['rationale']}",
                )
            else:
                raise HTTPException(
                    status_code=409,
                    detail=f"turn_payload_conflict: turn {body.turn_number} already processed with different message payload",
                )

    # Case B: Stale Turn (Old turn index smaller than stored current turn)
    if body.turn_number < stored_turn:
        raise HTTPException(
            status_code=400,
            detail=f"stale_turn_number: current conversation turn is {stored_turn}, received stale turn {body.turn_number}",
        )

    # Case C: Skipped Future Turn (Jumped ahead by more than 1 turn)
    if body.turn_number > stored_turn + 1:
        raise HTTPException(
            status_code=400,
            detail=f"out_of_order_turn: expected next turn {stored_turn + 1}, received future turn {body.turn_number}",
        )

    # 5. Deterministic Intent Classification
    intent, norm_msg = classify_intent(body.message)

    # 6. Fetch Contexts for Composition
    merchant_id = conv["merchant_id"]
    m_entity = store.get_context("merchant", merchant_id)
    m_payload = m_entity.get("payload", {}) if m_entity else {}

    cat_slug = conv.get("category_slug") or m_payload.get("category_slug")
    cat_entity = store.get_context("category", cat_slug) if cat_slug else None
    cat_payload = cat_entity.get("payload", {}) if cat_entity else {}

    trg_id = conv.get("trigger_id")
    trg_entity = store.get_context("trigger", trg_id) if trg_id else None
    trg_payload = trg_entity.get("payload", {}) if trg_entity else {}

    # Fact Extraction & Relevance Analysis
    fact_trace = GeneralRelevanceSelector.select(
        merchant=m_payload,
        category=cat_payload,
        trigger=trg_payload,
        inbound_query=body.message,
    )

    # 7. Sandboxed Sandwich Decision Pipeline
    # Step 7A: Compute baseline deterministic response (guaranteed fallback)
    det_response, det_next_state = compose_reply(
        intent=intent,
        raw_message=body.message,
        conversation_state=conv,
        merchant_context=m_payload,
        category_context=cat_payload,
        trigger_context=trg_payload,
    )

    response = det_response
    next_state = det_next_state
    is_deterministic_output = True
    llm_boundary_trace = LLMBoundaryTrace(invoked=False, invocation_reason="deterministic_intent_handled")
    llm_output_trace = LLMOutputTrace()

    # Step 7B: Assist with LLM only if pre-gate determines message is nuanced/ambiguous
    if should_use_llm(intent, body.message):
        t0 = time.time()
        try:
            envelope = build_context_envelope(
                store=store,
                conversation_id=body.conversation_id,
                merchant_id=merchant_id,
                category_slug=cat_slug,
                inbound_query=body.message,
                selected_facts=fact_trace.selected_facts,
            )
            llm_boundary_trace = LLMBoundaryTrace(
                invoked=True,
                invocation_reason="nuanced_or_ambiguous_inbound_message",
                envelope_fact_ids=[f.fact_id for f in envelope.supported_facts],
                envelope_summary={
                    "merchant_id": envelope.merchant.merchant_id,
                    "category": envelope.category.slug,
                    "facts_count": len(envelope.supported_facts),
                    "history_turns": len(envelope.conversation_history),
                },
            )
            llm_client = get_llm_client()
            suggestion = await llm_client.get_decision_suggestion(
                envelope=envelope,
                user_message=body.message,
                turn_number=body.turn_number,
            )
            llm_boundary_trace.latency_ms = (time.time() - t0) * 1000

            if suggestion is not None:
                llm_output_trace.raw_intent = suggestion.suggested_intent
                llm_output_trace.raw_action = suggestion.proposed_action
                llm_output_trace.raw_draft_body = suggestion.draft_body
                llm_output_trace.raw_cta = suggestion.proposed_cta
                llm_output_trace.raw_confidence = suggestion.confidence

                val_result = LLMOutputValidator.validate(
                    suggestion=suggestion,
                    envelope=envelope,
                    current_state=conv.get("current_state", ConversationState.AWAITING_REPLY.value),
                )
                llm_output_trace.validation_passed = val_result.is_valid
                llm_output_trace.validator_errors = val_result.error_reasons
                llm_output_trace.sanitized_body = val_result.sanitized_body
                llm_output_trace.sanitized_action = val_result.sanitized_action

                if val_result.is_valid and not val_result.fallback_required:
                    response = ReplyResponse(
                        action=val_result.sanitized_action,
                        body=val_result.sanitized_body,
                        cta=val_result.sanitized_cta,
                        wait_seconds=14400 if val_result.sanitized_action == "wait" else None,
                        rationale=f"[LLM-Assisted] {suggestion.rationale}",
                    )
                    is_deterministic_output = False
                    if suggestion.suggested_intent == "INTENT_AFFIRM":
                        next_state = ConversationState.ACTION_MODE
                    elif suggestion.suggested_intent == "INTENT_OPT_OUT":
                        next_state = ConversationState.TERMINATED_OPT_OUT
                    elif suggestion.suggested_intent == "INTENT_REJECT":
                        next_state = ConversationState.TERMINATED_DECLINED
                    else:
                        next_state = ConversationState.CLARIFYING
                else:
                    llm_boundary_trace.fallback_triggered = True
                    logger.info("LLM suggestion rejected by 11-point validator (%s); using deterministic baseline", val_result.error_reasons)
        except Exception as ex:
            llm_boundary_trace.fallback_triggered = True
            llm_boundary_trace.latency_ms = (time.time() - t0) * 1000
            logger.warning("LLM assistance failed (%s); seamlessly using deterministic baseline", type(ex).__name__)
            response = det_response
            next_state = det_next_state

    # 8. Terminal State Double Lock (HARD INVARIANT: Concluded thread must NEVER send)
    if conv.get("current_state") in (
        ConversationState.TERMINATED_OPT_OUT.value,
        ConversationState.TERMINATED_DECLINED.value,
        ConversationState.TERMINATED_AUTOREPLY.value,
        ConversationState.COMPLETED.value,
    ):
        response = ReplyResponse(
            action="end",
            body=None,
            cta=None,
            wait_seconds=None,
            rationale="Conversation is already concluded on this thread. No further actions permitted.",
        )
        next_state = ConversationState(conv["current_state"])

    # 9. Multi-Tenant Suppression Integration on Opt-Out
    if intent == ReplyIntent.INTENT_OPT_OUT or next_state == ConversationState.TERMINATED_OPT_OUT:
        store.record_suppression(
            suppression_key="merchant_opt_out",
            merchant_id=merchant_id,
            trigger_id="opt_out",
            sent_at=body.received_at,
        )
        if conv.get("suppression_key"):
            store.record_suppression(
                suppression_key=conv["suppression_key"],
                merchant_id=merchant_id,
                trigger_id="opt_out",
                sent_at=body.received_at,
            )

    # 10. Update Auto-Reply Count
    if intent == ReplyIntent.INTENT_AUTO_REPLY:
        auto_reply_count = int(conv.get("auto_reply_count", 0)) + 1
    else:
        auto_reply_count = int(conv.get("auto_reply_count", 0))

    # 11. Persist Updated Conversation State
    store.save_conversation(
        conversation_id=body.conversation_id,
        merchant_id=merchant_id,
        customer_id=body.customer_id or conv.get("customer_id"),
        trigger_id=conv.get("trigger_id"),
        suppression_key=conv.get("suppression_key"),
        category_slug=cat_slug,
        current_state=next_state.value,
        current_turn=body.turn_number,
        auto_reply_count=auto_reply_count,
        last_action=response.action,
        last_body=response.body,
        last_rationale=response.rationale,
        last_cta=response.cta,
        last_wait_seconds=response.wait_seconds,
        created_at=conv.get("created_at"),
    )

    # 12. Record Turn in SQLite
    store.record_turn(
        conversation_id=body.conversation_id,
        turn_number=body.turn_number,
        from_role=body.from_role,
        message=body.message,
        intent=intent.value,
        state_after=next_state.value,
        action=response.action,
        body=response.body,
        rationale=response.rationale,
        cta=response.cta,
        wait_seconds=response.wait_seconds,
        timestamp=body.received_at,
    )

    # 13. Persist Pipeline Decision Trace if enabled
    if is_debug_trace_enabled():
        trace = PipelineDecisionTrace(
            trace_id=f"trc_reply_{body.conversation_id}_t{body.turn_number}",
            timestamp=body.received_at,
            request_type="reply",
            merchant_id=merchant_id,
            conversation_id=body.conversation_id,
            raw_input=RawInputSummary(
                scopes_received=["conversation", "merchant", "category"],
                available_field_paths=[f.path for f in fact_trace.candidate_facts],
            ),
            gating=DeterministicGatingResult(
                gating_passed=True,
                is_terminal=conv.get("current_state") in (
                    ConversationState.TERMINATED_OPT_OUT.value,
                    ConversationState.TERMINATED_DECLINED.value,
                    ConversationState.TERMINATED_AUTOREPLY.value,
                    ConversationState.COMPLETED.value,
                ),
            ),
            fact_selection=fact_trace,
            llm_boundary=llm_boundary_trace,
            llm_output=llm_output_trace,
            final_output=FinalOutputTrace(
                action=response.action,
                body=response.body,
                cta=response.cta,
                is_deterministic=is_deterministic_output,
                conversation_id=body.conversation_id,
            ),
        )
        store.save_trace(trace)

    return response


@router.get("/debug/trace/{trace_id}")
async def get_debug_trace(
    trace_id: str,
    store: ContextStore = Depends(get_context_store),
):
    """Retrieve a stored decision trace by trace ID."""
    trace_data = store.get_trace(trace_id)
    if not trace_data:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace_data


@router.get("/debug/traces")
async def list_debug_traces(
    request_type: Optional[str] = None,
    merchant_id: Optional[str] = None,
    limit: int = 50,
    store: ContextStore = Depends(get_context_store),
):
    """List recent decision traces."""
    return store.list_traces(request_type=request_type, merchant_id=merchant_id, limit=limit)
