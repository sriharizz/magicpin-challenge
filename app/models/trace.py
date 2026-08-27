"""
Pipeline Decision Trace Data Models for Vera Observability.

Provides a strictly typed, immutable trace contract that records:
1. Raw input context & field paths
2. Deterministic gating outcomes (suppression, expiry, opt-out, subscription, replay)
3. Generic fact extraction & relevance decisions (candidates, selected, omitted + machine-readable reasons)
4. LLM boundary interactions (envelope, prompt metadata, provider, latency, timeouts)
5. LLM output validation (11-point validator results, sanitation, errors)
6. Final output synthesis (action, body, CTA, source of truth)
7. Judge evaluation metrics (if available)

STRICT RULE: Never record API keys, authentication credentials, or unredacted secret tokens.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class RawInputSummary(BaseModel):
    scopes_received: List[str] = Field(default_factory=list, description="Context scopes present in payload")
    available_field_paths: List[str] = Field(default_factory=list, description="Dot-notated paths of all non-empty fields")


class DeterministicGatingResult(BaseModel):
    suppression_status: Dict[str, Any] = Field(default_factory=dict, description="Suppression check results")
    is_expired: bool = Field(default=False, description="Whether trigger has passed expiration timestamp")
    category_match: bool = Field(default=True, description="Whether trigger and merchant category match")
    subscription_eligible: bool = Field(default=True, description="Whether merchant subscription is active")
    has_opted_out: bool = Field(default=False, description="Whether merchant has active opt-out / unsubscribe signal")
    is_terminal: bool = Field(default=False, description="Whether conversation is in terminal state")
    is_replay: bool = Field(default=False, description="Whether incoming message is duplicate turn replay")
    gating_passed: bool = Field(default=True, description="Overall deterministic gating verdict")
    rejection_reason: Optional[str] = Field(default=None, description="Reason if gating failed")


class TraceFactItem(BaseModel):
    fact_id: str = Field(description="Unique deterministic fact ID (e.g. F_MERCH_01, F_DIGEST_01)")
    path: str = Field(description="Dot-notated schema path (e.g. merchant.identity.owner_first_name)")
    value: Any = Field(description="Captured factual value")
    source_scope: Literal["category", "merchant", "customer", "trigger", "system"] = Field(description="Originating context scope")
    source_id: Optional[str] = Field(default=None, description="Entity identifier for the fact")
    allowed_triggers: List[str] = Field(default_factory=list, description="Trigger kinds where this fact is eligible")
    sensitivity: str = Field(default="public", description="Data sensitivity class (public, internal_metric, pii)")


class OmittedFactRecord(BaseModel):
    fact_id: str
    path: str
    reason: str = Field(description="Machine-readable omission reason code")
    detail: Optional[str] = None


class FactSelectionTrace(BaseModel):
    candidate_facts: List[TraceFactItem] = Field(default_factory=list, description="All extracted facts from raw payload")
    selected_facts: List[TraceFactItem] = Field(default_factory=list, description="Facts chosen by relevance analyzer")
    omitted_facts: List[OmittedFactRecord] = Field(default_factory=list, description="Facts evaluated but omitted")
    selection_reasons: Dict[str, str] = Field(default_factory=dict, description="Mapping of fact_id to selection rationale")


class LLMBoundaryTrace(BaseModel):
    invoked: bool = Field(default=False, description="Whether LLM was invoked for this decision")
    invocation_reason: str = Field(default="not_invoked", description="Reason for invoking or skipping LLM")
    envelope_fact_ids: List[str] = Field(default_factory=list, description="List of Fact IDs enclosed in LLM envelope")
    envelope_summary: Optional[Dict[str, Any]] = Field(default=None, description="Summary structure of envelope passed to LLM")
    provider: Optional[str] = Field(default=None, description="LLM provider name (e.g. groq, mock)")
    model: Optional[str] = Field(default=None, description="LLM model identifier")
    latency_ms: Optional[float] = Field(default=None, description="Round-trip LLM latency in milliseconds")
    timeout: bool = Field(default=False, description="Whether LLM call timed out")
    circuit_broken: bool = Field(default=False, description="Whether circuit breaker was open")
    fallback_triggered: bool = Field(default=False, description="Whether fallback engine was activated")


class LLMOutputTrace(BaseModel):
    raw_intent: Optional[str] = None
    raw_action: Optional[str] = None
    raw_draft_body: Optional[str] = None
    raw_cta: Optional[str] = None
    raw_confidence: Optional[float] = None
    validation_passed: bool = True
    validator_errors: List[str] = Field(default_factory=list)
    sanitized_body: Optional[str] = None
    sanitized_action: Optional[str] = None


class FinalOutputTrace(BaseModel):
    action: str = Field(description="Emitted action: send | wait | end")
    body: Optional[str] = Field(default=None, description="Emitted message body text")
    cta: Optional[str] = Field(default=None, description="Emitted call to action")
    is_deterministic: bool = Field(default=True, description="True if produced by deterministic composer")
    fallback_reason: Optional[str] = Field(default=None, description="Reason if deterministic fallback was used")
    conversation_id: Optional[str] = None


class JudgeEvaluationTrace(BaseModel):
    evaluator: Optional[str] = None
    total_score: Optional[float] = None
    specificity: Optional[float] = None
    category_fit: Optional[float] = None
    merchant_fit: Optional[float] = None
    decision_quality: Optional[float] = None
    engagement: Optional[float] = None
    penalties: Optional[float] = None
    hint: Optional[str] = None


class PipelineDecisionTrace(BaseModel):
    trace_id: str = Field(description="Unique trace identifier (e.g. trc_...)")
    timestamp: str = Field(description="ISO 8601 timestamp of trace execution")
    request_type: Literal["context", "tick", "reply"] = Field(description="Type of API request")
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    trigger_id: Optional[str] = None
    conversation_id: Optional[str] = None

    # Pipeline stages
    raw_input: RawInputSummary = Field(default_factory=RawInputSummary)
    gating: DeterministicGatingResult = Field(default_factory=DeterministicGatingResult)
    fact_selection: FactSelectionTrace = Field(default_factory=FactSelectionTrace)
    llm_boundary: LLMBoundaryTrace = Field(default_factory=LLMBoundaryTrace)
    llm_output: LLMOutputTrace = Field(default_factory=LLMOutputTrace)
    final_output: FinalOutputTrace = Field(default_factory=lambda: FinalOutputTrace(action="end"))
    evaluation: Optional[JudgeEvaluationTrace] = None
