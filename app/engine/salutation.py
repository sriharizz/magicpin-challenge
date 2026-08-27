"""
Salutation resolution engine driven entirely by CategoryContext.voice and MerchantContext.identity.
Zero hardcoded category checks.
"""

from typing import Any, Dict, List


def resolve_salutation(category: Dict[str, Any], merchant: Dict[str, Any]) -> str:
    """
    Resolve salutation dynamically using CategoryContext.voice.salutation_examples
    and MerchantContext.identity.

    Rules:
    1. CategoryContext.voice.salutation_examples is the single source of truth for greeting patterns.
    2. If pattern uses 'Dr.' prefix (e.g. 'Dr. {first_name}'), apply 'Dr. {name}'.
       If owner name is missing, use a safe category fallback like 'Doc' (if in examples) or 'Doctor'.
    3. If pattern uses 'Hi {first_name}' or custom salutation (e.g. '{first_name} ji'), format with owner name.
       If owner name is missing, fallback to '{business_name} team' or 'Hi there'.
    4. Never output 'Dr. None' or 'Hi None'.
    """
    voice = category.get("voice", {}) if isinstance(category, dict) else {}
    salutation_examples: List[str] = voice.get("salutation_examples", []) if isinstance(voice, dict) else []

    identity = merchant.get("identity", {}) if isinstance(merchant, dict) else {}
    owner_first_name = identity.get("owner_first_name")
    biz_name = identity.get("name")

    clean_name = ""
    if owner_first_name:
        candidate = str(owner_first_name).strip()
        if candidate.lower() not in ("none", "null", ""):
            clean_name = candidate

    clean_biz = ""
    if biz_name:
        candidate_biz = str(biz_name).strip()
        if candidate_biz.lower() not in ("none", "null", ""):
            clean_biz = candidate_biz

    # Check if category voice specifies a 'Dr.' style salutation
    is_doctor_pattern = any("dr." in str(ex).lower() or "doc" in str(ex).lower() for ex in salutation_examples)

    if is_doctor_pattern:
        if clean_name:
            lower = clean_name.lower()
            if lower.startswith("dr."):
                return f"Dr. {clean_name[3:].strip()}"
            elif lower.startswith("dr "):
                return f"Dr. {clean_name[3:].strip()}"
            else:
                return f"Dr. {clean_name}"

        # Missing owner name fallback for clinical/doctor verticals
        for ex in salutation_examples:
            ex_str = str(ex).strip()
            if "{" not in ex_str and ex_str:  # Non-templated static fallback like "Doc"
                return ex_str
        return "Doctor"

    # Check for custom template patterns in salutation_examples (e.g. "{first_name} ji", "Dear {first_name}")
    for ex in salutation_examples:
        ex_str = str(ex).strip()
        if "{first_name}" in ex_str and clean_name:
            return ex_str.replace("{first_name}", clean_name)

    # General category pattern (e.g. Salons, Restaurants, Gyms, Pharmacies, Retail)
    if clean_name:
        return f"Hi {clean_name}"
    elif clean_biz:
        return f"Hi {clean_biz} team"

    return "Hi there"
