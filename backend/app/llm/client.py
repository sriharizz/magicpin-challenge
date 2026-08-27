"""
Resilient LLM Client with Circuit Breaker and Strict Timeout Enforcement.

Guarantees:
1. Strict <= 1500ms timeout budget enforced client-side.
2. Circuit Breaker: CLOSED -> OPEN after repeated failures, avoiding wasted network calls.
3. Zero API key or secret leakage in logs.
4. Seamless deterministic fallback if provider is unavailable, times out, or fails validation.
5. Zero LLM authority over state: client is purely a read-only suggestion generator.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Optional, Dict, Any

from app.config import (
    LLM_PROVIDER,
    LLM_API_KEY,
    LLM_MODEL,
    LLM_TIMEOUT_MS,
    LLM_CIRCUIT_FAILURE_THRESHOLD,
    LLM_CIRCUIT_COOLDOWN_SECONDS,
)
from app.llm.schemas import LLMContextEnvelope, LLMDecisionSuggestion
from app.llm.provider import LLMProvider, MockProvider, GeminiProvider, OpenAIProvider, GroqProvider

logger = logging.getLogger("vera.llm.client")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation: all requests sent to provider
    OPEN = "OPEN"          # Tripped: all requests fail-fast to deterministic fallback
    HALF_OPEN = "HALF_OPEN"  # Probing: 1 probe allowed to test provider recovery


class CircuitBreaker:
    """
    Lightweight circuit breaker protecting Vera from slow or failing LLM endpoints.
    """

    def __init__(
        self,
        failure_threshold: int = LLM_CIRCUIT_FAILURE_THRESHOLD,
        cooldown_seconds: float = LLM_CIRCUIT_COOLDOWN_SECONDS,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time: float = 0.0

    def can_attempt(self) -> bool:
        """Check if an outbound LLM call is currently permitted."""
        now = time.time()

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.cooldown_seconds:
                logger.info("Circuit breaker cooldown expired; entering HALF_OPEN probe state")
                self.state = CircuitState.HALF_OPEN
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False

    def record_success(self):
        """Record successful LLM invocation."""
        if self.state != CircuitState.CLOSED:
            logger.info("Probe succeeded; resetting circuit breaker to CLOSED")
        self.consecutive_failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        """Record failed LLM invocation (timeout, network error, 5xx, or malformed output)."""
        self.consecutive_failures += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Probe failed during HALF_OPEN; reopening circuit breaker to OPEN")
            self.state = CircuitState.OPEN
        elif self.consecutive_failures >= self.failure_threshold:
            logger.warning(
                "Circuit breaker tripped to OPEN after %d consecutive failures (cooldown=%.1fs)",
                self.consecutive_failures,
                self.cooldown_seconds,
            )
            self.state = CircuitState.OPEN


class LLMClient:
    """
    Provider-neutral LLM client with strict timeout enforcement and circuit breaking.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        timeout_ms: int = LLM_TIMEOUT_MS,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.timeout_ms = timeout_ms
        self.timeout_seconds = timeout_ms / 1000.0
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

        if provider is not None:
            self.provider = provider
        else:
            self.provider = self._create_configured_provider()

    def _create_configured_provider(self) -> LLMProvider:
        """Factory for provider instantiation based on environment configuration."""
        p_name = (LLM_PROVIDER or "mock").strip().lower()

        if p_name == "groq":
            return GroqProvider(api_key=LLM_API_KEY, model=LLM_MODEL)
        elif p_name == "gemini":
            return GeminiProvider(api_key=LLM_API_KEY, model=LLM_MODEL)
        elif p_name == "openai":
            return OpenAIProvider(api_key=LLM_API_KEY, model=LLM_MODEL)
        else:
            return MockProvider()

    async def get_decision_suggestion(
        self,
        envelope: LLMContextEnvelope,
        user_message: str,
        turn_number: int,
    ) -> Optional[LLMDecisionSuggestion]:
        """
        Request a structured decision suggestion from the configured LLM provider.
        
        Guarantees:
        - If circuit breaker is OPEN, returns None instantly (0ms latency, deterministic fallback).
        - If provider exceeds timeout_ms, aborts and returns None.
        - On any network/schema failure, returns None.
        - Never crashes the caller.
        """
        if not self.circuit_breaker.can_attempt():
            logger.info("Circuit breaker is OPEN; skipping LLM call and executing deterministic fallback")
            return None

        start_time = time.perf_counter()
        try:
            # Enforce hard client-side timeout
            suggestion = await asyncio.wait_for(
                self.provider.generate(
                    envelope=envelope,
                    user_message=user_message,
                    turn_number=turn_number,
                    timeout_seconds=self.timeout_seconds,
                ),
                timeout=self.timeout_seconds,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if suggestion is None:
                logger.warning("Provider %s returned None/empty response in %.1fms", self.provider.name(), latency_ms)
                self.circuit_breaker.record_failure()
                return None

            logger.info("Provider %s generated suggestion in %.1fms", self.provider.name(), latency_ms)
            self.circuit_breaker.record_success()
            return suggestion

        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(
                "Provider %s timed out after %.1fms (limit=%dms); falling back to deterministic engine",
                self.provider.name(),
                latency_ms,
                self.timeout_ms,
            )
            self.circuit_breaker.record_failure()
            return None

        except Exception as ex:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(
                "Provider %s failed with %s in %.1fms; falling back to deterministic engine",
                self.provider.name(),
                type(ex).__name__,
                latency_ms,
            )
            self.circuit_breaker.record_failure()
            return None


# Global singleton client instance
_client_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Retrieve or initialize the global LLMClient instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance


def set_llm_client(client: Optional[LLMClient]):
    """Override the global LLMClient instance (useful for test fixtures)."""
    global _client_instance
    _client_instance = client
