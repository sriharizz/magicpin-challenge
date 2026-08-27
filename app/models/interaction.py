"""
Pydantic models for Tick and Reply endpoints (/v1/tick, /v1/reply).
Phase 1 includes typed models and clean baseline stubs.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TickRequest(BaseModel):
    now: str = Field(..., description="Current simulated ISO 8601 timestamp")
    available_triggers: List[str] = Field(default_factory=list, description="Active trigger IDs for this tick")


class TickAction(BaseModel):
    conversation_id: str = Field(..., description="Unique ID for this conversation thread")
    merchant_id: str = Field(..., description="Target merchant ID")
    customer_id: Optional[str] = Field(None, description="Optional target customer ID for cx outreach")
    send_as: str = Field("vera", description="Sender role: 'vera' or 'merchant_on_behalf'")
    trigger_id: str = Field(..., description="Trigger ID that prompted this message")
    template_name: str = Field(..., description="Meta-approved WhatsApp template name")
    template_params: List[str] = Field(default_factory=list, description="Template placeholder values")
    body: str = Field(..., description="Composed WhatsApp message text")
    cta: str = Field(..., description="Call to action type: binary, open_ended, none")
    suppression_key: str = Field(..., description="Deduplication key for suppressing repeat sends")
    rationale: str = Field(..., description="Explanation of why this message was composed")


class TickResponse(BaseModel):
    actions: List[TickAction] = Field(default_factory=list, description="List of proactive message actions")


class ReplyRequest(BaseModel):
    conversation_id: str = Field(..., description="Existing conversation thread ID")
    merchant_id: Optional[str] = Field(None, description="Merchant ID involved in conversation")
    customer_id: Optional[str] = Field(None, description="Customer ID if customer-facing conversation")
    from_role: str = Field(..., description="Role of sender: 'merchant' or 'customer'")
    message: str = Field(..., description="Message received from merchant or customer")
    received_at: str = Field(..., description="ISO 8601 timestamp of received reply")
    turn_number: int = Field(..., ge=1, description="Sequential turn index in conversation")


class ReplyResponse(BaseModel):
    action: str = Field(..., description="Next action: 'send', 'wait', or 'end'")
    body: Optional[str] = Field(None, description="Response message body if action is 'send'")
    cta: Optional[str] = Field(None, description="Call to action type if sending a message")
    wait_seconds: Optional[int] = Field(None, description="Seconds to back off if action is 'wait'")
    rationale: str = Field(..., description="Explanation of why this action was chosen")
