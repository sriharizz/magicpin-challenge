"""
Vera LLM Integration Package.

Exports:
- LLMContextEnvelope, LLMDecisionSuggestion, ValidationResult
- build_context_envelope, format_user_prompt, SYSTEM_PROMPT
- LLMOutputValidator
- LLMProvider, MockProvider, GeminiProvider, OpenAIProvider
- LLMClient, CircuitBreaker, CircuitState, get_llm_client, set_llm_client
"""

from app.llm.schemas import (
    LLMContextEnvelope,
    LLMDecisionSuggestion,
    ValidationResult,
    SupportedFact,
    MerchantEnvelope,
    CategoryEnvelope,
    DigestItemEnvelope,
)
from app.llm.prompts import (
    SYSTEM_PROMPT,
    build_context_envelope,
    format_user_prompt,
)
from app.llm.validator import (
    LLMOutputValidator,
)
from app.llm.provider import (
    LLMProvider,
    MockProvider,
    GeminiProvider,
    OpenAIProvider,
)
from app.llm.client import (
    LLMClient,
    CircuitBreaker,
    CircuitState,
    get_llm_client,
    set_llm_client,
)

__all__ = [
    "LLMContextEnvelope",
    "LLMDecisionSuggestion",
    "ValidationResult",
    "SupportedFact",
    "MerchantEnvelope",
    "CategoryEnvelope",
    "DigestItemEnvelope",
    "SYSTEM_PROMPT",
    "build_context_envelope",
    "format_user_prompt",
    "LLMOutputValidator",
    "LLMProvider",
    "MockProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "LLMClient",
    "CircuitBreaker",
    "CircuitState",
    "get_llm_client",
    "set_llm_client",
]
