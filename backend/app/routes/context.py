"""
Context Ingestion Route (/v1/context).

Handles push updates for all four context scopes:
- category
- merchant
- customer
- trigger

Follows strict versioning invariants:
- First version  -> 200 Accepted (Stored)
- Same version   -> 200 Accepted (Idempotent No-Op)
- Higher version -> 200 Accepted (Atomically Replaced)
- Lower version  -> 409 Conflict (Rejected as stale)
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.config import is_debug_trace_enabled
from app.models.context import (
    ContextPushRequest,
    ContextPushSuccessResponse,
    ContextConflictResponse,
)
from app.models.trace import PipelineDecisionTrace, RawInputSummary, DeterministicGatingResult
from app.store.context_store import ContextStore, get_context_store

router = APIRouter(prefix="/v1", tags=["Context"])


@router.post(
    "/context",
    response_model=ContextPushSuccessResponse,
    responses={
        status.HTTP_200_OK: {"model": ContextPushSuccessResponse},
        status.HTTP_409_CONFLICT: {"model": ContextConflictResponse},
    },
)
async def push_context(
    body: ContextPushRequest,
    store: ContextStore = Depends(get_context_store),
):
    """
    Ingest a context payload with atomic version validation.
    """
    accepted, current_version, stored_at = store.save_context(
        scope=body.scope.value,
        context_id=body.context_id,
        version=body.version,
        payload=body.payload,
        delivered_at=body.delivered_at,
    )

    if is_debug_trace_enabled():
        trace = PipelineDecisionTrace(
            trace_id=f"trc_ctx_{body.scope.value}_{body.context_id}_v{body.version}",
            timestamp=stored_at,
            request_type="context",
            merchant_id=body.context_id if body.scope.value == "merchant" else None,
            raw_input=RawInputSummary(
                scopes_received=[body.scope.value],
                available_field_paths=[f"{body.scope.value}.{k}" for k in body.payload.keys()] if isinstance(body.payload, dict) else [],
            ),
            gating=DeterministicGatingResult(
                gating_passed=accepted,
                rejection_reason="stale_version" if not accepted else None,
            ),
        )
        store.save_trace(trace)

    if not accepted:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "accepted": False,
                "reason": "stale_version",
                "current_version": current_version,
            },
        )

    ack_id = f"ack_{body.context_id}_v{body.version}"
    return ContextPushSuccessResponse(
        accepted=True,
        ack_id=ack_id,
        stored_at=stored_at,
    )
