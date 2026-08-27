"""
Pydantic models for Context operations (/v1/context).
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ContextScope(str, Enum):
    CATEGORY = "category"
    MERCHANT = "merchant"
    CUSTOMER = "customer"
    TRIGGER = "trigger"


class ContextPushRequest(BaseModel):
    scope: ContextScope = Field(..., description="Scope of the context: category, merchant, customer, trigger")
    context_id: str = Field(..., min_length=1, description="Unique identifier for the context entity")
    version: int = Field(..., ge=1, description="Positive integer version of this context payload")
    payload: Dict[str, Any] = Field(..., description="Full structured JSON payload for the context")
    delivered_at: str = Field(..., description="ISO 8601 timestamp when judge/source delivered this context")


class ContextPushSuccessResponse(BaseModel):
    accepted: bool = Field(True, description="Indicates whether the context push was accepted and stored")
    ack_id: str = Field(..., description="Acknowledgment ID in format ack_{context_id}_v{version}")
    stored_at: str = Field(..., description="ISO 8601 timestamp when context was saved/acknowledged")


class ContextConflictResponse(BaseModel):
    accepted: bool = Field(False, description="Always false for version conflict")
    reason: str = Field("stale_version", description="Reason for conflict")
    current_version: int = Field(..., description="Highest version already stored in the system")


class ContextErrorResponse(BaseModel):
    accepted: bool = Field(False, description="Always false for errors")
    reason: str = Field(..., description="Short error reason code (e.g., invalid_scope, malformed_payload)")
    details: Optional[str] = Field(None, description="Descriptive error detail")
