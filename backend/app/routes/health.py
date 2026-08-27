"""
Health and Metadata Routes (/v1/healthz, /v1/metadata).
"""

import time
from fastapi import APIRouter, Depends

from app.config import (
    START_TIME,
    TEAM_NAME,
    TEAM_MEMBERS,
    MODEL_NAME,
    APPROACH,
    CONTACT_EMAIL,
    APP_VERSION,
    SUBMITTED_AT,
)
from app.models.health import ContextCounts, HealthResponse, MetadataResponse
from app.store.context_store import ContextStore, get_context_store

router = APIRouter(prefix="/v1", tags=["Health & Metadata"])


@router.get("/healthz", response_model=HealthResponse)
async def get_healthz(store: ContextStore = Depends(get_context_store)) -> HealthResponse:
    """Liveness & readiness probe returning uptime and loaded context counts across all 4 scopes."""
    uptime = max(0, int(time.time() - START_TIME))
    counts = store.get_counts()
    return HealthResponse(
        status="ok",
        uptime_seconds=uptime,
        contexts_loaded=ContextCounts(**counts),
    )


@router.get("/metadata", response_model=MetadataResponse)
async def get_metadata() -> MetadataResponse:
    """Bot metadata describing team, model, version, approach, and contact info."""
    return MetadataResponse(
        team_name=TEAM_NAME,
        team_members=TEAM_MEMBERS,
        model=MODEL_NAME,
        approach=APPROACH,
        contact_email=CONTACT_EMAIL,
        version=APP_VERSION,
        submitted_at=SUBMITTED_AT,
    )
