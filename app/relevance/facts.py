"""
Generic Fact Representation and Extraction Layer for Vera (Phase 7F).

Extracts typed, dot-notated Fact objects with explicit provenance and semantic roles
from arbitrary context payloads (merchant, category, customer, trigger)
without hardcoding scenario-specific schemas or benchmark strings.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
import hashlib


class FactRole(str, Enum):
    """
    Semantic operational role of an atomic fact within the context envelope.
    """
    IDENTITY = "IDENTITY"                       # Person or business salutation name
    PRIMARY_TRIGGER_EVIDENCE = "PRIMARY_TRIGGER"# Directly referenced trigger payload / active article
    ACTIONABLE_EVIDENCE = "ACTIONABLE"          # Actionable advice, recommendation, checklist, offer
    COHORT_EVIDENCE = "COHORT"                  # Patient / customer demographic aggregate or segment
    SPECIFICITY_EVIDENCE = "SPECIFICITY"        # Exact numeric sample sizes (N), percentages, counts
    TEMPORAL_EVIDENCE = "TEMPORAL"              # Expiration dates, days remaining, freshness timestamps
    GEOGRAPHIC_EVIDENCE = "GEOGRAPHIC"          # Locality, city (local neighborhood context)
    DISTRACTING_OR_SENSITIVE = "DISTRACTING"    # Sensitive billing, card numbers, internal arrears, passwords
    SUPPORTING_EVIDENCE = "SUPPORTING"          # Voice guidelines, allowed vocab, generic metadata


class Fact(BaseModel):
    """
    Typed, explainable factual atomic unit extracted from context scopes.
    Preserves exact provenance and semantic role for LLM grounding.
    """
    fact_id: str = Field(description="Deterministic identifier for this fact")
    path: str = Field(description="Dot-notated schema path (e.g. merchant.identity.owner_first_name)")
    value: Any = Field(description="Extracted value (primitive, list, or dict)")
    value_type: str = Field(default="string", description="Primitive data type: numeric, string, boolean, list")
    source_scope: Literal["category", "merchant", "customer", "trigger", "system"] = Field(description="Source context scope")
    source_id: Optional[str] = Field(default=None, description="Identifier of the source entity")
    role: FactRole = Field(default=FactRole.SUPPORTING_EVIDENCE, description="Semantic operational role")
    provenance: str = Field(default="", description="Human-readable provenance trace (e.g. 'merchant.customer_aggregate')")
    relational_target: Optional[str] = Field(default=None, description="Referenced entity ID if fact establishes a relationship")
    allowed_triggers: List[str] = Field(default_factory=list, description="Trigger kinds where this fact is semantically valid")
    sensitivity: str = Field(default="public", description="Data sensitivity tier: public, internal_metric, or pii")
    freshness: Optional[str] = Field(default=None, description="Timestamp or staleness indicator")

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "path": self.path,
            "value": str(self.value) if not isinstance(self.value, (str, int, float, bool)) else self.value,
            "role": self.role.value,
            "provenance": self.provenance,
            "source_scope": self.source_scope,
        }


class FactExtractor:
    """
    Recursively extracts atomic facts and infers semantic roles from arbitrary context dictionaries.
    """

    @staticmethod
    def _generate_fact_id(scope: str, path: str) -> str:
        clean_path = path.replace(".", "_").replace("[", "_").replace("]", "").upper()
        # Deterministic short hash to prevent collisions
        short_hash = hashlib.md5(f"{scope}:{path}".encode("utf-8")).hexdigest()[:4].upper()
        return f"F_{scope[:3].upper()}_{clean_path}_{short_hash}"

    @classmethod
    def _infer_value_type(cls, val: Any) -> str:
        if isinstance(val, bool):
            return "boolean"
        elif isinstance(val, (int, float)):
            return "numeric"
        elif isinstance(val, list):
            return "list"
        return "string"

    @classmethod
    def _infer_fact_role(cls, path: str, val: Any, sensitivity: str) -> FactRole:
        """
        Infer semantic operational role purely from structural path patterns and data types.
        Zero hardcoded scenario strings.
        """
        lower_path = path.lower()

        # Sensitive / Distracting
        if sensitivity == "pii" and not any(k in lower_path for k in ["name", "first_name"]):
            return FactRole.DISTRACTING_OR_SENSITIVE
        if any(s in lower_path for s in ["card_last4", "arrears", "secret", "password", "token", "balance"]):
            return FactRole.DISTRACTING_OR_SENSITIVE

        # Identity
        if any(k in lower_path for k in ["identity.owner_first_name", "identity.doctor_name", "identity.name", "proprietor_name"]):
            return FactRole.IDENTITY

        # Actionable Guidance & Offers
        if any(k in lower_path for k in ["actionable", "checklist", "recommendation", "cta", "offers"]):
            return FactRole.ACTIONABLE_EVIDENCE

        # Cohort Demographics
        if any(k in lower_path for k in ["customer_aggregate", "patient_segment", "cohort", "audience"]):
            return FactRole.COHORT_EVIDENCE

        # Specificity Grounding (Sample size, verified rates, numeric metrics)
        if "trial_n" in lower_path or (isinstance(val, (int, float)) and val > 0 and any(k in lower_path for k in ["count", "size", "rate", "n="])):
            return FactRole.SPECIFICITY_EVIDENCE

        # Geographic Grounding
        if any(k in lower_path for k in ["locality", "city", "location", "neighborhood"]):
            return FactRole.GEOGRAPHIC_EVIDENCE

        # Temporal Grounding
        if any(k in lower_path for k in ["days_remaining", "expires_at", "timestamp", "established_year", "date"]):
            return FactRole.TEMPORAL_EVIDENCE

        # Primary Trigger / Digest Payload
        if any(k in lower_path for k in ["digest[", "items[", "title", "summary", "payload"]):
            return FactRole.PRIMARY_TRIGGER_EVIDENCE

        return FactRole.SUPPORTING_EVIDENCE

    @classmethod
    def extract_from_dict(
        cls,
        data: Dict[str, Any],
        scope: Literal["category", "merchant", "customer", "trigger", "system"],
        source_id: Optional[str] = None,
        prefix: str = "",
    ) -> List[Fact]:
        """
        Recursively extract dot-notated facts from a dictionary payload.
        """
        facts: List[Fact] = []
        if not isinstance(data, dict):
            return facts

        for key, val in data.items():
            current_path = f"{prefix}.{key}" if prefix else f"{scope}.{key}"
            
            # Skip empty / null values
            if val is None or val == "" or val == [] or val == {}:
                continue

            if isinstance(val, dict):
                facts.extend(cls.extract_from_dict(val, scope, source_id, current_path))
            elif isinstance(val, list):
                if all(isinstance(elem, (str, int, float, bool)) for elem in val):
                    fact_id = cls._generate_fact_id(scope, current_path)
                    val_type = "list"
                    sens = "internal_metric" if "signal" in current_path else "public"
                    role = cls._infer_fact_role(current_path, val, sens)
                    facts.append(
                        Fact(
                            fact_id=fact_id,
                            path=current_path,
                            value=val,
                            value_type=val_type,
                            source_scope=scope,
                            source_id=source_id,
                            role=role,
                            provenance=f"{scope}:{current_path}",
                            sensitivity=sens,
                        )
                    )
                else:
                    for idx, item in enumerate(val):
                        if isinstance(item, dict):
                            item_id = item.get("id") or str(idx)
                            item_prefix = f"{current_path}[{item_id}]"
                            facts.extend(cls.extract_from_dict(item, scope, source_id, item_prefix))
            else:
                fact_id = cls._generate_fact_id(scope, current_path)
                val_type = cls._infer_value_type(val)
                sens = "public"
                if any(metric in current_path for metric in ["performance", "leads", "revenue", "calls", "views"]):
                    sens = "internal_metric"
                elif any(pii in current_path for pii in ["phone", "email", "owner_first_name", "doctor_name"]):
                    sens = "pii"

                role = cls._infer_fact_role(current_path, val, sens)
                facts.append(
                    Fact(
                        fact_id=fact_id,
                        path=current_path,
                        value=val,
                        value_type=val_type,
                        source_scope=scope,
                        source_id=source_id,
                        role=role,
                        provenance=f"{scope}:{current_path}",
                        sensitivity=sens,
                    )
                )

        return facts

    @classmethod
    def extract_all_contexts(
        cls,
        merchant: Optional[Dict[str, Any]] = None,
        category: Optional[Dict[str, Any]] = None,
        customer: Optional[Dict[str, Any]] = None,
        trigger: Optional[Dict[str, Any]] = None,
    ) -> List[Fact]:
        """
        Extract facts from all available context scopes simultaneously.
        """
        all_facts: List[Fact] = []
        if merchant:
            m_id = merchant.get("merchant_id") or merchant.get("id")
            all_facts.extend(cls.extract_from_dict(merchant, "merchant", m_id))
        if category:
            c_id = category.get("slug") or category.get("id")
            all_facts.extend(cls.extract_from_dict(category, "category", c_id))
        if customer:
            cust_id = customer.get("customer_id") or customer.get("id")
            all_facts.extend(cls.extract_from_dict(customer, "customer", cust_id))
        if trigger:
            trg_id = trigger.get("id") or trigger.get("trigger_id")
            all_facts.extend(cls.extract_from_dict(trigger, "trigger", trg_id))

        return all_facts
