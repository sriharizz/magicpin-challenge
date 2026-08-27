"""
Structure-Driven, Role-Budgeted Context Relevance Selector for Vera (Phase 7F).

Replaces procedural path-matching, trigger-name substring checking, and naive sorting
with an explainable, structure-driven relevance scoring and role-aware budgeting engine:

Score = (
    w_trigger * trigger_affinity
  + w_entity * entity_affinity
  + w_cohort * cohort_affinity
  + w_action * actionability
  + w_spec * specificity_value
  + w_geo * geographic_value
  + w_temp * temporal_freshness
  - w_distract * distraction_risk
  - w_sens * sensitivity_penalty
)

Principles:
1. Zero hardcoding of scenario names, case IDs, merchant names, or benchmark lookups.
2. Structure-driven trigger intent binding (derives trigger domain from payload relationships).
3. Role-aware context budgeting (guarantees Slot 1 for Identity, Slots 2-4 for Primary Content, Slots 5-6 for Cohort/Actionable).
4. Minimum Sufficient Context optimization (never dumps irrelevant context).
5. 100% explainability: every fact receives a full dimensional feature trace.
"""

from typing import Any, Dict, List, Optional, Tuple, Set
from pydantic import BaseModel, Field
import re

from app.relevance.facts import Fact, FactRole, FactExtractor
from app.models.trace import OmittedFactRecord, FactSelectionTrace, TraceFactItem


class FactRelevanceFeatures(BaseModel):
    """
    Normalized multi-dimensional semantic relevance features for a candidate fact [0.0 - 1.0].
    """
    trigger_affinity: float = Field(default=0.0, description="Semantic alignment with trigger intent domain")
    entity_affinity: float = Field(default=0.0, description="Direct relevance to primary merchant identity/profile")
    cohort_affinity: float = Field(default=0.0, description="Alignment with customer cohort or target audience")
    actionability: float = Field(default=0.0, description="Whether fact directly empowers a decision or next step")
    specificity_value: float = Field(default=0.0, description="Concrete grounding value (numeric sample sizes, rates)")
    geographic_value: float = Field(default=0.0, description="Local relevance without unnecessary demographic clutter")
    temporal_freshness: float = Field(default=0.5, description="Recency and operational validity")
    distraction_risk: float = Field(default=0.0, description="Risk of clashing with tone or diverting message focus")
    sensitivity_penalty: float = Field(default=0.0, description="Risk of leaking private billing or confidential data")
    
    total_score: float = Field(default=0.0, description="Composite weighted relevance score")
    decision_reason: str = Field(default="", description="Explainable machine-readable reason for score")


# Calibrated feature weights for structure-driven retrieval
FEATURE_WEIGHTS = {
    "w_trigger": 3.0,
    "w_entity": 2.0,
    "w_cohort": 2.0,
    "w_action": 1.5,
    "w_spec": 1.5,
    "w_geo": 1.0,
    "w_temp": 0.5,
    "w_distract": 3.5,
    "w_sens": 4.0,
}

# Selection threshold for fact inclusion
MIN_RELEVANCE_THRESHOLD = 3.0

# Maximum facts budget per envelope to prevent context dumping
MAX_ENVELOPE_FACT_BUDGET = 6


class GeneralRelevanceSelector:
    """
    General, structure-driven context relevance selector with role-aware budgeting.
    """

    @classmethod
    def compute_features(
        cls,
        fact: Fact,
        trigger_context: Optional[Dict[str, Any]] = None,
        category_context: Optional[Dict[str, Any]] = None,
        inbound_query: Optional[str] = None,
    ) -> FactRelevanceFeatures:
        """
        Extract explainable dimensional features for a single candidate fact.
        Derives intent from structural payload references rather than trigger name strings.
        """
        trigger = trigger_context or {}
        category = category_context or {}
        trg_payload = trigger.get("payload", {})
        path = fact.path
        val = fact.value
        role = fact.role

        # 1. Structural Trigger Binding (Zero dependency on trigger name strings!)
        referenced_item_id = trg_payload.get("top_item_id") or trg_payload.get("item_id")
        has_digest_context = bool(referenced_item_id or category.get("digest") or category.get("items"))
        has_metric_ref = bool(any(k in trg_payload for k in ["drop_pct", "growth_pct", "window_days", "metric_name"]))
        has_sub_ref = bool(any(k in trg_payload for k in ["days_remaining", "plan_id", "subscription_status"]))
        is_inbound = bool(inbound_query is not None)

        trigger_aff = 0.0
        if has_digest_context:
            if referenced_item_id:
                if f"[{referenced_item_id}]" in path:
                    trigger_aff = 1.0  # Directly referenced active item
                elif "category.digest[" in path or "category.items[" in path:
                    trigger_aff = -0.5  # Unmatched candidate item
                elif role in (FactRole.COHORT_EVIDENCE, FactRole.IDENTITY):
                    trigger_aff = 0.8  # Cohort / doctor identity relevant to digest
                elif role == FactRole.DISTRACTING_OR_SENSITIVE or "performance" in path or "offers" in path:
                    trigger_aff = -0.8  # Commercial clash with educational context
                else:
                    trigger_aff = 0.3
            else:
                # No specific item referenced, evaluate first digest item
                if role in (FactRole.PRIMARY_TRIGGER_EVIDENCE, FactRole.SPECIFICITY_EVIDENCE, FactRole.ACTIONABLE_EVIDENCE):
                    trigger_aff = 0.9
                elif role in (FactRole.COHORT_EVIDENCE, FactRole.IDENTITY):
                    trigger_aff = 0.8
                elif "performance" in path or "offers" in path:
                    trigger_aff = -0.8
                else:
                    trigger_aff = 0.3
        elif has_metric_ref:
            if "performance" in path or role == FactRole.SPECIFICITY_EVIDENCE:
                trigger_aff = 1.0
            elif "offers" in path or role == FactRole.ACTIONABLE_EVIDENCE:
                trigger_aff = 0.6
            elif "category.digest" in path:
                trigger_aff = -0.6
            else:
                trigger_aff = 0.3
        elif has_sub_ref:
            if "subscription" in path or role == FactRole.TEMPORAL_EVIDENCE:
                trigger_aff = 1.0
            elif "category.digest" in path:
                trigger_aff = -0.8
            else:
                trigger_aff = 0.3
        elif is_inbound:
            # Query token overlap matching
            q_tokens = [w.lower() for w in re.findall(r'\b\w{3,}\b', inbound_query or "")]
            val_str = str(val).lower()
            if any(t in val_str for t in q_tokens) or any(t in path.lower() for t in q_tokens):
                trigger_aff = 1.0
            elif role == FactRole.IDENTITY:
                trigger_aff = 0.8
            else:
                trigger_aff = 0.4
        else:
            trigger_aff = 0.4

        # 2. Entity Affinity (Identity and Category Voice)
        entity_aff = 0.0
        if role == FactRole.IDENTITY:
            if "owner_first_name" in path or "doctor_name" in path:
                entity_aff = 1.5  # Crucial for personalized salutation
            else:
                entity_aff = 1.0  # Business entity name
        elif "category.voice" in path:
            entity_aff = 0.8

        # 3. Cohort Affinity (Customer / Patient demographics)
        cohort_aff = 0.0
        if role == FactRole.COHORT_EVIDENCE:
            cohort_aff = 1.0
            digest_items = category.get("digest", []) or category.get("digest_items", [])
            if digest_items and isinstance(digest_items[0], dict):
                seg = str(digest_items[0].get("patient_segment", "")).lower()
                if seg and seg not in ("all", "general", "none"):
                    seg_tokens = [t for t in seg.replace("_", " ").split() if len(t) > 2]
                    if any(t in path.lower() for t in seg_tokens):
                        cohort_aff = 1.5

        # 4. Actionability
        action = 0.0
        if role == FactRole.ACTIONABLE_EVIDENCE:
            action = 1.0
        elif role == FactRole.IDENTITY and ("owner_first_name" in path or "doctor_name" in path):
            action = 0.8  # Directly enables personal doctor greeting

        # 5. Specificity Value (Numeric grounding vs generic text)
        spec = 0.0
        if role == FactRole.SPECIFICITY_EVIDENCE or (isinstance(val, (int, float)) and val > 0):
            spec = 0.9  # Concrete empirical metric
        elif isinstance(val, str) and len(val) >= 10 and not val.startswith("http"):
            spec = 0.7  # Informative textual body

        # 6. Geographic Relevance
        geo = 0.0
        if role == FactRole.GEOGRAPHIC_EVIDENCE:
            if has_metric_ref or is_inbound:
                geo = 0.8
            elif has_digest_context:
                geo = 0.3

        # 7. Temporal Freshness
        temp = 0.5
        if role == FactRole.TEMPORAL_EVIDENCE:
            temp = 0.9
        elif fact.freshness:
            temp = 0.8

        # 8. Distraction Risk
        distract = 0.0
        if has_digest_context:
            if "performance.revenue" in path or "performance.views" in path or "offers" in path:
                distract = 1.0  # Commercial vanity distraction in clinical context
            elif "subscription.status" in path or "merchant_id" in path:
                distract = 0.7
        elif has_sub_ref:
            if "category.digest" in path:
                distract = 0.9
        elif is_inbound:
            if any(s in path for s in ["arrears", "card_last4", "balance", "internal_"]):
                if not (inbound_query and any(t in inbound_query.lower() for t in ["bill", "plan", "pay", "card", "fee", "invoice", "cost"])):
                    distract = 1.0

        # 9. Sensitivity Penalty
        sens = 0.0
        if role == FactRole.DISTRACTING_OR_SENSITIVE or any(s in path for s in ["card_last4", "arrears", "secret", "password", "token"]):
            sens = 1.0
        elif fact.sensitivity == "pii" and role != FactRole.IDENTITY:
            sens = 1.0
        elif fact.sensitivity == "internal_metric" and has_digest_context:
            sens = 0.8

        # Composite Score Calculation
        composite = (
            FEATURE_WEIGHTS["w_trigger"] * trigger_aff
            + FEATURE_WEIGHTS["w_entity"] * entity_aff
            + FEATURE_WEIGHTS["w_cohort"] * cohort_aff
            + FEATURE_WEIGHTS["w_action"] * action
            + FEATURE_WEIGHTS["w_spec"] * spec
            + FEATURE_WEIGHTS["w_geo"] * geo
            + FEATURE_WEIGHTS["w_temp"] * temp
            - FEATURE_WEIGHTS["w_distract"] * distract
            - FEATURE_WEIGHTS["w_sens"] * sens
        )

        reason = "scored_above_threshold" if composite >= MIN_RELEVANCE_THRESHOLD else "omitted_low_relevance_score"
        if distract > 0.7:
            reason = "omitted_context_distraction_risk"
        elif sens > 0.7:
            reason = "omitted_data_sensitivity_policy"
        elif trigger_aff < 0:
            reason = "omitted_trigger_domain_mismatch"

        return FactRelevanceFeatures(
            trigger_affinity=round(trigger_aff, 2),
            entity_affinity=round(entity_aff, 2),
            cohort_affinity=round(cohort_aff, 2),
            actionability=round(action, 2),
            specificity_value=round(spec, 2),
            geographic_value=round(geo, 2),
            temporal_freshness=round(temp, 2),
            distraction_risk=round(distract, 2),
            sensitivity_penalty=round(sens, 2),
            total_score=round(composite, 2),
            decision_reason=reason,
        )

    @classmethod
    def select(
        cls,
        merchant: Optional[Dict[str, Any]] = None,
        category: Optional[Dict[str, Any]] = None,
        customer: Optional[Dict[str, Any]] = None,
        trigger: Optional[Dict[str, Any]] = None,
        inbound_query: Optional[str] = None,
        budget: int = MAX_ENVELOPE_FACT_BUDGET,
    ) -> FactSelectionTrace:
        """
        Execute generic structure-driven scoring and Role-Aware Salience Budgeting.
        """
        merchant = merchant or {}
        category = category or {}
        customer = customer or {}
        trigger = trigger or {}

        # 1. Extract candidate facts
        all_facts = FactExtractor.extract_all_contexts(merchant, category, customer, trigger)

        # 2. Score candidate facts
        scored_by_role: Dict[FactRole, List[Tuple[Fact, FactRelevanceFeatures]]] = {
            r: [] for r in FactRole
        }
        all_scored: List[Tuple[Fact, FactRelevanceFeatures]] = []

        for fact in all_facts:
            feat = cls.compute_features(
                fact=fact,
                trigger_context=trigger,
                category_context=category,
                inbound_query=inbound_query,
            )
            scored_by_role[fact.role].append((fact, feat))
            all_scored.append((fact, feat))

        # Sort each role bucket descending by score
        for role_list in scored_by_role.values():
            role_list.sort(key=lambda item: item[1].total_score, reverse=True)

        selected_facts: List[Fact] = []
        selected_ids: Set[str] = set()
        selection_reasons: Dict[str, str] = {}

        def _try_add_fact(fact: Fact, feat: FactRelevanceFeatures, slot_name: str) -> bool:
            if len(selected_facts) >= budget:
                return False
            if fact.fact_id in selected_ids:
                return False
            if feat.total_score < MIN_RELEVANCE_THRESHOLD:
                return False
            selected_facts.append(fact)
            selected_ids.add(fact.fact_id)
            selection_reasons[fact.fact_id] = f"{feat.decision_reason} [{slot_name}] (score={feat.total_score})"
            return True

        # 3. Role-Aware Salience Budget Allocation
        # Slot 1: Guaranteed Salutation Identity
        for fact, feat in scored_by_role[FactRole.IDENTITY]:
            if _try_add_fact(fact, feat, "slot_identity"):
                break

        # Slots 2–4: Primary Trigger Content & Exact Specificity
        primary_candidates = scored_by_role[FactRole.PRIMARY_TRIGGER_EVIDENCE] + scored_by_role[FactRole.SPECIFICITY_EVIDENCE]
        primary_candidates.sort(key=lambda item: item[1].total_score, reverse=True)
        for fact, feat in primary_candidates:
            if len(selected_facts) >= 4:
                break
            _try_add_fact(fact, feat, "slot_primary_content")

        # Slots 5–6: Supporting Cohort Demographics & Actionable Protocols
        supporting_candidates = scored_by_role[FactRole.COHORT_EVIDENCE] + scored_by_role[FactRole.ACTIONABLE_EVIDENCE] + scored_by_role[FactRole.GEOGRAPHIC_EVIDENCE]
        supporting_candidates.sort(key=lambda item: item[1].total_score, reverse=True)
        for fact, feat in supporting_candidates:
            if len(selected_facts) >= budget:
                break
            _try_add_fact(fact, feat, "slot_cohort_actionable")

        # Fill remaining open budget slots with any remaining high-scoring facts >= 3.0
        all_scored.sort(key=lambda item: item[1].total_score, reverse=True)
        for fact, feat in all_scored:
            if len(selected_facts) >= budget:
                break
            _try_add_fact(fact, feat, "slot_fill")

        # 4. Compile explainable omitted records
        omitted_records: List[OmittedFactRecord] = []
        for fact, feat in all_scored:
            if fact.fact_id not in selected_ids:
                reason = feat.decision_reason
                if feat.total_score >= MIN_RELEVANCE_THRESHOLD and len(selected_facts) >= budget:
                    reason = "omitted_budget_limit_exceeded"
                omitted_records.append(
                    OmittedFactRecord(
                        fact_id=fact.fact_id,
                        path=fact.path,
                        reason=reason,
                        detail=f"Score {feat.total_score} (thresh={MIN_RELEVANCE_THRESHOLD}, budget={budget})",
                    )
                )

        trace_candidates = [
            TraceFactItem(
                fact_id=f.fact_id,
                path=f.path,
                value=f.value,
                source_scope=f.source_scope,
                source_id=f.source_id,
                allowed_triggers=f.allowed_triggers,
                sensitivity=f.sensitivity,
            )
            for f in all_facts
        ]

        trace_selected = [
            TraceFactItem(
                fact_id=f.fact_id,
                path=f.path,
                value=f.value,
                source_scope=f.source_scope,
                source_id=f.source_id,
                allowed_triggers=f.allowed_triggers,
                sensitivity=f.sensitivity,
            )
            for f in selected_facts
        ]

        return FactSelectionTrace(
            candidate_facts=trace_candidates,
            selected_facts=trace_selected,
            omitted_facts=omitted_records,
            selection_reasons=selection_reasons,
        )
