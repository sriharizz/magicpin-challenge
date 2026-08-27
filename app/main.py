"""
magicpin Vera AI Challenge — Backend Application Entrypoint

=============================================================================
CORE VERA PRINCIPLES (MANDATORY OPERATIONAL INVARIANTS)
=============================================================================
1. Ground everything in received context.
2. Never invent numbers, offers, dates, customer facts, or claims.
3. Handle category + merchant + trigger correctly.
4. Decide before writing.
5. Specificity is more important than generic AI copy.
6. Merchant fit is more important than generic personalization.
7. One strong CTA per message.
8. Sometimes the correct decision is wait, suppress, or end.
9. Never repeat messages or ignore suppression.
10. If the merchant clearly says YES / GO AHEAD, execute rather than continuing to qualify unnecessarily.
11. Repeated auto-replies must eventually cause backoff/end behavior.
12. Hostile or opt-out responses must stop outreach.
13. Customer outreach must respect the supplied customer context and consent.
14. New context versions must replace stale context correctly.
15. Same input should produce deterministic behavior.
16. Keep responses fast (<30s requirement, targets <50ms local).
17. The real judge will inject unseen context, so never hardcode the sample scenarios.
18. Build small and deterministic before adding sophistication.
=============================================================================
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import APP_NAME, APP_VERSION
from app.routes.health import router as health_router
from app.routes.context import router as context_router
from app.routes.interaction import router as interaction_router
from app.store.context_store import get_context_store

logger = logging.getLogger("vera.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema is ready
    store = get_context_store()
    store.init_db()
    yield
    # Teardown logic if needed


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Deterministic context-driven engine for magicpin Vera AI Challenge",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    """Production-safe observability middleware adding request ID and timing."""
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    start_time = time.perf_counter()

    try:
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error("Unhandled error processing %s %s (%s): %s", request.method, request.url.path, type(exc).__name__, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "accepted": False,
                "reason": "internal_error",
                "details": "An unexpected error occurred while processing the request.",
            },
            headers={"X-Request-ID": request_id, "X-Response-Time-Ms": f"{duration_ms:.2f}"},
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Format validation errors into the challenge contract format.
    """
    errors = exc.errors()
    details = "; ".join([f"{e.get('loc', [])}: {e.get('msg', '')}" for e in errors])

    # Check if this was an invalid scope error on /v1/context
    is_scope_error = any("scope" in [str(loc) for loc in e.get("loc", [])] for e in errors)
    reason = "invalid_scope" if is_scope_error else "malformed_request"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "accepted": False,
            "reason": reason,
            "details": details,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all safety exception handler preventing internal stack trace leaks."""
    logger.error("Global catch-all error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "accepted": False,
            "reason": "internal_error",
            "details": "An unexpected error occurred while processing the request.",
        },
    )


# Register all /v1 endpoint routers
app.include_router(health_router)
app.include_router(context_router)
app.include_router(interaction_router)


@app.get("/")
async def root():
    """Root redirect / info probe."""
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "endpoints": [
            "GET /v1/healthz",
            "GET /v1/metadata",
            "POST /v1/context",
            "POST /v1/tick",
            "POST /v1/reply",
        ],
    }
