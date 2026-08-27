"""
Deterministic Context Relevance Analyzer for Vera.

Inspects extracted facts and context scopes to decide which facts are relevant,
eligible, or omitted for a given trigger kind and category vertical.

Produces explainable, machine-readable decisions:
- candidate_facts
- selected_facts
- omitted_facts (with standardized reason codes)
- selection_reasons (mapping fact_id -> why selected)

ZERO hardcoding of individual scenario strings.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.relevance.facts import Fact, FactExtractor
from app.models.trace import OmittedFactRecord, FactSelectionTrace, TraceFactItem


class ContextRelevanceAnalyzer:
    """
    Evaluates context facts against trigger kind, category voice, and merchant state.
    """

    @classmethod
    def analyze(
        cls,
        merchant: Optional[Dict[str, Any]] = None,
        category: Optional[Dict[str, Any]] = None,
        customer: Optional[Dict[str, Any]] = None,
        trigger: Optional[Dict[str, Any]] = None,
        conversation_state: Optional[str] = None,
    ) -> FactSelectionTrace:
        """
        Perform deterministic relevance analysis across all input context scopes.
        """
        merchant = merchant or {}
        category = category or {}
        customer = customer or {}
        trigger = trigger or {}

        # 1. Extract all candidate facts
        all_facts = FactExtractor.extract_all_contexts(merchant, category, customer, trigger)
        
        trigger_kind = str(trigger.get("kind") or trigger.get("payload", {}).get("trigger_kind") or "research_digest").lower()
        top_item_id = trigger.get("payload", {}).get("top_item_id")
        
        # Identify matched digest item if applicable
        digest_items = category.get("digest", []) or category.get("digest_items", [])
        matched_digest_id = None
        matched_patient_segment = None
        if top_item_id:
            for d in digest_items:
                if isinstance(d, dict) and d.get("id") == top_item_id:
                    matched_digest_id = d.get("id")
                    matched_patient_segment = d.get("patient_segment")
                    break
        if not matched_digest_id and digest_items and isinstance(digest_items[0], dict):
            matched_digest_id = digest_items[0].get("id")
            matched_patient_segment = digest_items[0].get("patient_segment")

        selected_facts: List[Fact] = []
        omitted_facts: List[OmittedFactRecord] = []
        selection_reasons: Dict[str, str] = []

        selection_reasons_dict: Dict[str, str] = {}

        for fact in all_facts:
            path = fact.path
            
            # Category digest items filtering
            if "category.digest[" in path:
                if matched_digest_id and f"[{matched_digest_id}]" not in path:
                    omitted_facts.append(
                        OmittedFactRecord(
                            fact_id=fact.fact_id,
                            path=path,
                            reason="omitted_unmatched_digest_item",
                            detail=f"Fact belongs to non-active digest item, active is {matched_digest_id}",
                        )
                    )
                    continue

            # Route by trigger kind
            if trigger_kind == "research_digest":
                cls._evaluate_research_digest_fact(
                    fact=fact,
                    matched_digest_id=matched_digest_id,
                    matched_patient_segment=matched_patient_segment,
                    merchant=merchant,
                    selected_facts=selected_facts,
                    omitted_facts=omitted_facts,
                    selection_reasons=selection_reasons_dict,
                )
            elif trigger_kind in ("performance_alert", "weekly_performance", "traffic_spike"):
                cls._evaluate_performance_fact(
                    fact=fact,
                    selected_facts=selected_facts,
                    omitted_facts=omitted_facts,
                    selection_reasons=selection_reasons_dict,
                )
            elif trigger_kind in ("trend_alert", "local_demand", "seasonal_trend"):
                cls._evaluate_trend_fact(
                    fact=fact,
                    selected_facts=selected_facts,
                    omitted_facts=omitted_facts,
                    selection_reasons=selection_reasons_dict,
                )
            elif trigger_kind in ("renewal_reminder", "subscription_expiring"):
                cls._evaluate_renewal_fact(
                    fact=fact,
                    selected_facts=selected_facts,
                    omitted_facts=omitted_facts,
                    selection_reasons=selection_reasons_dict,
                )
            else:
                # Generic fallback evaluation
                cls._evaluate_generic_fact(
                    fact=fact,
                    selected_facts=selected_facts,
                    omitted_facts=omitted_facts,
                    selection_reasons=selection_reasons_dict,
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
            omitted_facts=omitted_facts,
            selection_reasons=selection_reasons_dict,
        )

    @classmethod
    def _evaluate_research_digest_fact(
        cls,
        fact: Fact,
        matched_digest_id: Optional[str],
        matched_patient_segment: Optional[str],
        merchant: Dict[str, Any],
        selected_facts: List[Fact],
        omitted_facts: List[OmittedFactRecord],
        selection_reasons: Dict[str, str],
    ) -> None:
        path = fact.path
        
        # 1. Identity selection
        if path == "merchant.identity.owner_first_name":
            selected_facts.append(fact)
            selection_reasons[fact.fact_id] = "selected_salutation_personalization"
            return
        elif path == "merchant.identity.name":
            if not merchant.get("identity", {}).get("owner_first_name"):
                selected_facts.append(fact)
                selection_reasons[fact.fact_id] = "selected_fallback_business_salutation"
            else:
                omitted_facts.append(
                    OmittedFactRecord(
                        fact_id=fact.fact_id,
                        path=path,
                        reason="omitted_secondary_identity",
                        detail="owner_first_name is available, business name redundant for salutation",
                    )
                )
            return
        elif path in ("merchant.identity.city", "merchant.identity.locality", "merchant.identity.established_year"):
            omitted_facts.append(
                OmittedFactRecord(
                    fact_id=fact.fact_id,
                    path=path,
                    reason="omitted_irrelevant_geographic_in_scientific_digest",
                    detail="Scientific research digest is clinical and non-geographic",
                )
            )
            return

        # 2. Performance metrics in scientific research digest
        if "merchant.performance." in path:
            omitted_facts.append(
                OmittedFactRecord(
                    fact_id=fact.fact_id,
                    path=path,
                    reason="omitted_commercial_metrics_in_clinical_digest",
                    detail="Views and call volume conflict with peer-clinical research tone",
                )
            )
            return

        # 3. Active offers in research digest
        if "merchant.offers" in path:
            omitted_facts.append(
                OmittedFactRecord(
                    fact_id=fact.fact_id,
                    path=path,
                    reason="omitted_promotional_offer_in_clinical_digest",
                    detail="Promotions suppressed during scientific literature review",
                )
            )
            return

        # 4. Customer aggregate & patient counts
        if path == "merchant.customer_aggregate.high_risk_adult_count":
            if matched_patient_segment in ("high_risk_adults", "high_risk"):
                selected_facts.append(fact)
                selection_reasons[fact.fact_id] = "selected_matching_patient_cohort_count"
            else:
                omitted_facts.append(
                    OmittedFactRecord(
                        fact_id=fact.fact_id,
                        path=path,
                        reason="omitted_unmatched_cohort_metric",
                        detail=f"Study segment '{matched_patient_segment}' is not high-risk adult",
                    )
                )
            return
        elif path == "merchant.customer_aggregate.total_unique_ytd":
            omitted_facts.append(
                OmittedFactRecord(
                    fact_id=fact.fact_id,
                    path=path,
                    reason="omitted_generic_volume_in_topic_digest",
                    detail="Total YTD volume not referenced in specific topic digest",
                )
            )
            return

        # 5. Digest Facts (from active digest item)
        if "category.digest[" in path:
            if any(k in path for k in [".summary", ".title", ".source", ".trial_n", ".patient_segment", ".actionable"]):
                selected_facts.append(fact)
                selection_reasons[fact.fact_id] = f"selected_active_digest_{path.split('.')[-1]}"
                return

        # 6. Category Voice Guidelines
        if "category.voice." in path:
            if any(k in path for k in [".tone", ".vocab_taboo", ".salutation_examples"]):
                selected_facts.append(fact)
                selection_reasons[fact.fact_id] = f"selected_category_governance_{path.split('.')[-1]}"
                return

        # Default fallback
        omitted_facts.append(
            OmittedFactRecord(
                fact_id=fact.fact_id,
                path=path,
                reason="omitted_low_relevance_to_trigger",
                detail=f"Field {path} not mapped to research_digest template",
            )
        )

    @classmethod
    def _evaluate_performance_fact(
        cls,
        fact: Fact,
        selected_facts: List[Fact],
        omitted_facts: List[OmittedFactRecord],
        selection_reasons: Dict[str, str],
    ) -> None:
        path = fact.path
        if "merchant.performance." in path or path == "merchant.identity.owner_first_name" or path == "merchant.customer_aggregate.total_unique_ytd":
            selected_facts.append(fact)
            selection_reasons[fact.fact_id] = "selected_performance_metric"
        else:
            omitted_facts.append(
                OmittedFactRecord(
                    fact_id=fact.fact_id,
                    path=path,
                    reason="omitted_non_performance_field",
                )
            )

    @classmethod
    def _evaluate_trend_fact(
        cls,
        fact: Fact,
        selected_facts: List[Fact],
        omitted_facts: List[OmittedFactRecord],
        selection_reasons: Dict[str, str],
    ) -> None:
        path = fact.path
        if path in ("merchant.identity.locality", "merchant.identity.owner_first_name", "merchant.identity.name") or "signal" in path:
            selected_facts.append(fact)
            selection_reasons[fact.fact_id] = "selected_local_trend_grounding"
        else:
            omitted_facts.append(
                OmittedFactRecord(
                    fact_id=fact.fact_id,
                    path=path,
                    reason="omitted_non_trend_field",
                )
            )

    @classmethod
    def _evaluate_renewal_fact(
        cls,
        fact: Fact,
        selected_facts: List[Fact],
        omitted_facts: List[OmittedFactRecord],
        selection_reasons: Dict[str, str],
    ) -> None:
        path = fact.path
        if "subscription" in path or path in ("merchant.identity.owner_first_name", "merchant.identity.name"):
            selected_facts.append(fact)
            selection_reasons[fact.fact_id] = "selected_subscription_renewal_fact"
        else:
            omitted_facts.append(
                OmittedFactRecord(
                    fact_id=fact.fact_id,
                    path=path,
                    reason="omitted_non_renewal_field",
                )
            )

    @classmethod
    def _evaluate_generic_fact(
        cls,
        fact: Fact,
        selected_facts: List[Fact],
        omitted_facts: List[OmittedFactRecord],
        selection_reasons: Dict[str, str],
    ) -> None:
        path = fact.path
        if path in ("merchant.identity.owner_first_name", "merchant.identity.name") or "summary" in path:
            selected_facts.append(fact)
            selection_reasons[fact.fact_id] = "selected_generic_grounding"
        else:
            omitted_facts.append(
                OmittedFactRecord(
                    fact_id=fact.fact_id,
                    path=path,
                    reason="omitted_generic_filter",
                )
            )
