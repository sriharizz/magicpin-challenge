"""
Pydantic Schemas for LLM Integration Contract in Vera.

Defines:
1. LLMContextEnvelope: Strictly grounded input context passed to the LLM.
2. LLMDecisionSuggestion: Structured decision and response draft proposed by the LLM.
3. ValidationResult: Deterministic audit outcome of the LLM suggestion.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class SupportedFact(BaseModel):
    fact_id: str = Field(description="Unique identifier for the fact, e.g. F1, F2")
    key: str = Field(description="Property name, e.g. trial_n, caries_reduction")
    value: str = Field(description="Exact value as specified in context, e.g. 2,100 or 38%")
    description: str = Field(description="Contextual meaning of the fact")


class DigestItemEnvelope(BaseModel):
    item_id: str
    title: str
    source: str
    summary: str
    trial_n: Optional[int] = None
    key_takeaway: Optional[str] = None


class CategoryVoiceEnvelope(BaseModel):
    tone: Optional[str] = "peer_clinical"
    taboo_words: List[str] = Field(default_factory=list)


class CategoryEnvelope(BaseModel):
    slug: str
    voice: CategoryVoiceEnvelope = Field(default_factory=CategoryVoiceEnvelope)


class MerchantEnvelope(BaseModel):
    merchant_id: str
    name: Optional[str] = None
    category_slug: Optional[str] = None
    tone_preference: Optional[str] = None


class TurnHistoryItem(BaseModel):
    turn: int
    role: Literal["vera", "merchant", "customer"]
    message: str


class LLMContextEnvelope(BaseModel):
    """Minimal typed context envelope supplied to the LLM."""
    merchant: MerchantEnvelope
    category: CategoryEnvelope
    active_digest_item: Optional[DigestItemEnvelope] = None
    supported_facts: List[SupportedFact] = Field(default_factory=list)
    conversation_history: List[TurnHistoryItem] = Field(default_factory=list)


class LLMDecisionSuggestion(BaseModel):
    """Strict structured response format emitted by the LLM."""
    suggested_intent: Literal[
        "INTENT_AFFIRM",
        "INTENT_REJECT",
        "INTENT_QUESTION",
        "INTENT_OUT_OF_SCOPE",
        "INTENT_UNKNOWN",
    ] = Field(description="Classified merchant intent")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")
    proposed_action: Literal["send", "wait", "end"] = Field(description="Lifecycle action for /v1/reply")
    response_strategy: str = Field(description="Brief explanation of the chosen communication strategy")
    draft_body: Optional[str] = Field(default=None, description="Proposed customer-facing message body")
    proposed_cta: Optional[Literal["binary_yes_no", "open_ended", "quick_reply", "calendar", "none"]] = Field(
        default=None, description="Call to action format"
    )
    cited_fact_ids: List[str] = Field(
        default_factory=list, description="List of Fact IDs (e.g. ['F1', 'F2']) cited in draft_body"
    )
    unknown_facts_requested: List[str] = Field(
        default_factory=list, description="Facts requested by merchant but absent from context envelope"
    )
    rationale: str = Field(description="Audit trail explaining the decision rationale")


class ValidationResult(BaseModel):
    """Outcome of the 11-point deterministic validation gate."""
    is_valid: bool
    sanitized_body: Optional[str] = None
    sanitized_action: Literal["send", "wait", "end"] = "send"
    sanitized_cta: Optional[str] = None
    error_reasons: List[str] = Field(default_factory=list)
    fallback_required: bool = False
