"""
Unit, Resilience, and Latency Tests for Vera's LLM Client and Circuit Breaker (Phase 5B).
"""

import asyncio
import time
import pytest
from app.llm.schemas import (
    LLMContextEnvelope,
    MerchantEnvelope,
    CategoryEnvelope,
    CategoryVoiceEnvelope,
    DigestItemEnvelope,
    SupportedFact,
    LLMDecisionSuggestion,
)
from app.llm.provider import MockProvider, GeminiProvider, OpenAIProvider
from app.llm.client import LLMClient, CircuitBreaker, CircuitState
from app.llm.validator import LLMOutputValidator
from app.engine.reply_composer import compose_reply
from app.engine.intents import ReplyIntent


@pytest.fixture
def sample_envelope() -> LLMContextEnvelope:
    return LLMContextEnvelope(
        merchant=MerchantEnvelope(
            merchant_id="m_001_drmeera",
            name="Dr. Meera's Clinic",
            category_slug="dentists",
            tone_preference="peer_clinical",
        ),
        category=CategoryEnvelope(
            slug="dentists",
            voice=CategoryVoiceEnvelope(
                tone="peer_clinical",
                taboo_words=["guaranteed", "miracle", "100%"],
            ),
        ),
        active_digest_item=DigestItemEnvelope(
            item_id="d_fluoride_2026",
            title="High-viscosity GIC trial",
            source="JIDA Oct 2026",
            summary="38% caries reduction in root caries.",
            trial_n=2100,
        ),
        supported_facts=[
            SupportedFact(fact_id="F1", key="trial_n", value="2,100", description="Trial sample size"),
            SupportedFact(fact_id="F2", key="caries_reduction", value="38%", description="Caries reduction rate"),
        ],
    )


@pytest.mark.asyncio
async def test_successful_provider_response(sample_envelope):
    """Verify clean response from provider returns valid suggestion."""
    mock = MockProvider(mode="success")
    client = LLMClient(provider=mock, timeout_ms=1500)

    suggestion = await client.get_decision_suggestion(sample_envelope, "Yes please send", 2)
    assert suggestion is not None
    assert suggestion.suggested_intent == "INTENT_AFFIRM"
    assert suggestion.proposed_action == "send"
    assert "F1" in suggestion.cited_fact_ids
    assert client.circuit_breaker.state == CircuitState.CLOSED
    assert client.circuit_breaker.consecutive_failures == 0


@pytest.mark.asyncio
async def test_provider_timeout_falls_back(sample_envelope):
    """Verify provider timeout (exceeding timeout_ms) returns None without crashing."""
    mock = MockProvider(mode="timeout")
    client = LLMClient(provider=mock, timeout_ms=300)  # Use 300ms for fast test execution

    start = time.perf_counter()
    suggestion = await client.get_decision_suggestion(sample_envelope, "Yes please", 2)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert suggestion is None
    assert elapsed_ms < 700.0  # Timeout enforced promptly
    assert client.circuit_breaker.consecutive_failures == 1


@pytest.mark.asyncio
async def test_network_exception_falls_back(sample_envelope):
    """Verify network connection failure returns None and records failure."""
    mock = MockProvider(mode="network_error")
    client = LLMClient(provider=mock, timeout_ms=1500)

    suggestion = await client.get_decision_suggestion(sample_envelope, "Yes", 2)
    assert suggestion is None
    assert client.circuit_breaker.consecutive_failures == 1


@pytest.mark.asyncio
async def test_http_429_rate_limit_falls_back(sample_envelope):
    """Verify HTTP 429 returns None and increments circuit failures."""
    mock = MockProvider(mode="http_429")
    client = LLMClient(provider=mock, timeout_ms=1500)

    suggestion = await client.get_decision_suggestion(sample_envelope, "Yes", 2)
    assert suggestion is None
    assert client.circuit_breaker.consecutive_failures == 1


@pytest.mark.asyncio
async def test_http_500_server_error_falls_back(sample_envelope):
    """Verify HTTP 500 returns None."""
    mock = MockProvider(mode="http_500")
    client = LLMClient(provider=mock, timeout_ms=1500)

    suggestion = await client.get_decision_suggestion(sample_envelope, "Yes", 2)
    assert suggestion is None
    assert client.circuit_breaker.consecutive_failures == 1


@pytest.mark.asyncio
async def test_malformed_json_falls_back(sample_envelope):
    """Verify malformed unparseable JSON returns None."""
    mock = MockProvider(mode="malformed_json")
    client = LLMClient(provider=mock, timeout_ms=1500)

    suggestion = await client.get_decision_suggestion(sample_envelope, "Yes", 2)
    assert suggestion is None
    assert client.circuit_breaker.consecutive_failures == 1


@pytest.mark.asyncio
async def test_invalid_structured_output_falls_back(sample_envelope):
    """Verify invalid schema response returns None."""
    mock = MockProvider(mode="invalid_schema")
    client = LLMClient(provider=mock, timeout_ms=1500)

    suggestion = await client.get_decision_suggestion(sample_envelope, "Yes", 2)
    assert suggestion is None
    assert client.circuit_breaker.consecutive_failures == 1


@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open_after_3_failures(sample_envelope):
    """Verify 3 consecutive failures trips the circuit breaker to OPEN."""
    mock = MockProvider(mode="network_error")
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=2.0)
    client = LLMClient(provider=mock, timeout_ms=500, circuit_breaker=cb)

    assert cb.state == CircuitState.CLOSED

    # Failure 1
    await client.get_decision_suggestion(sample_envelope, "msg 1", 2)
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 1

    # Failure 2
    await client.get_decision_suggestion(sample_envelope, "msg 2", 2)
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 2

    # Failure 3 -> Trips to OPEN
    await client.get_decision_suggestion(sample_envelope, "msg 3", 2)
    assert cb.state == CircuitState.OPEN
    assert cb.consecutive_failures == 3


@pytest.mark.asyncio
async def test_open_circuit_skips_provider_call(sample_envelope):
    """Verify that when circuit is OPEN, client immediately returns None without calling provider."""
    mock = MockProvider(mode="success")
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10.0)
    cb.state = CircuitState.OPEN
    cb.last_failure_time = time.time()  # Recent failure

    client = LLMClient(provider=mock, timeout_ms=1500, circuit_breaker=cb)

    start = time.perf_counter()
    suggestion = await client.get_decision_suggestion(sample_envelope, "msg", 2)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert suggestion is None
    assert mock.call_count == 0  # Provider was never called
    assert elapsed_ms < 5.0  # Ultra-fast immediate fallback (<5ms)


@pytest.mark.asyncio
async def test_half_open_recovery_probe_success(sample_envelope):
    """Verify that after cooldown, circuit enters HALF_OPEN, probes provider, and returns to CLOSED on success."""
    mock = MockProvider(mode="success")
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)  # 100ms cooldown
    cb.state = CircuitState.OPEN
    cb.last_failure_time = time.time() - 0.2  # Cooldown already expired

    client = LLMClient(provider=mock, timeout_ms=1500, circuit_breaker=cb)

    # Calling client should transition to HALF_OPEN, probe provider, and reset to CLOSED
    suggestion = await client.get_decision_suggestion(sample_envelope, "msg", 2)
    assert suggestion is not None
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0


@pytest.mark.asyncio
async def test_half_open_recovery_probe_failure_reopens(sample_envelope):
    """Verify that if probe fails during HALF_OPEN, circuit immediately reopens."""
    mock = MockProvider(mode="network_error")
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
    cb.state = CircuitState.OPEN
    cb.last_failure_time = time.time() - 0.2

    client = LLMClient(provider=mock, timeout_ms=1500, circuit_breaker=cb)

    suggestion = await client.get_decision_suggestion(sample_envelope, "msg", 2)
    assert suggestion is None
    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_gemini_and_openai_missing_keys_handled_safely(sample_envelope):
    """Verify Gemini and OpenAI adapters handle missing API keys gracefully without crashing."""
    gemini = GeminiProvider(api_key="", model="gemini-2.0-flash")
    openai = OpenAIProvider(api_key="", model="gpt-4o-mini")

    res_gemini = await gemini.generate(sample_envelope, "Hello", 2)
    assert res_gemini is None

    res_openai = await openai.generate(sample_envelope, "Hello", 2)
    assert res_openai is None


def test_existing_deterministic_engine_remains_unaffected():
    """Verify deterministic reply engine runs unchanged with 100% determinism."""
    resp, next_state = compose_reply(
        intent=ReplyIntent.INTENT_AFFIRM,
        raw_message="yes please send",
        conversation_state={"auto_reply_count": 0, "current_turn": 1},
        category_context={"voice": {"taboo_words": []}, "digest": [{"summary": "clinical trial", "trial_n": 2100}]},
        merchant_context={"identity": {"name": "Dr. Meera"}},
    )
    assert resp.action == "send"
    assert resp.body is not None
    assert "sending" in resp.body.lower() or "draft" in resp.body.lower()
    assert next_state.value == "ACTION_MODE"


@pytest.mark.asyncio
async def test_full_sandwich_pipeline_simulation(sample_envelope):
    """Simulate complete sandwich flow: Envelope -> Client -> Validator -> Fallback."""
    # Scenario A: Approved LLM Output
    mock_approved = MockProvider(mode="success")
    client_a = LLMClient(provider=mock_approved)
    sugg_a = await client_a.get_decision_suggestion(sample_envelope, "Yes send it", 2)
    assert sugg_a is not None

    val_a = LLMOutputValidator.validate(sugg_a, sample_envelope, current_state="AWAITING_REPLY")
    assert val_a.is_valid is True
    assert val_a.fallback_required is False

    # Scenario B: Disapproved LLM Output (Qualifying Language)
    unapproved_sugg = LLMDecisionSuggestion(
        suggested_intent="INTENT_AFFIRM",
        confidence=0.9,
        proposed_action="send",
        response_strategy="qualify",
        draft_body="Would you like me to send the abstract?",
        proposed_cta="binary_yes_no",
        cited_fact_ids=["F1"],
        rationale="Qualifying.",
    )
    mock_bad = MockProvider(custom_suggestion=unapproved_sugg)
    client_b = LLMClient(provider=mock_bad)
    sugg_b = await client_b.get_decision_suggestion(sample_envelope, "Yes", 2)
    val_b = LLMOutputValidator.validate(sugg_b, sample_envelope, current_state="AWAITING_REPLY")
    assert val_b.is_valid is False
    assert val_b.fallback_required is True

    # Fallback to deterministic engine
    fallback_resp, _ = compose_reply(
        intent=ReplyIntent.INTENT_AFFIRM,
        raw_message="Yes",
        conversation_state={"auto_reply_count": 0, "current_turn": 1},
        category_context={"voice": {"taboo_words": []}, "digest": [{"summary": "clinical trial", "trial_n": 2100}]},
        merchant_context={"identity": {"name": "Dr. Meera"}},
    )
    assert fallback_resp.action == "send"
    assert "would you" not in fallback_resp.body.lower()


@pytest.mark.asyncio
async def test_performance_benchmarks_all_paths(sample_envelope):
    """Measure latency across deterministic, LLM success, LLM timeout, and circuit-open paths."""
    # 1. Deterministic path
    t0 = time.perf_counter()
    compose_reply(ReplyIntent.INTENT_AFFIRM, "yes", {"auto_reply_count": 0, "current_turn": 1})
    lat_deterministic_ms = (time.perf_counter() - t0) * 1000.0

    # 2. LLM Success path (Mock)
    client_success = LLMClient(provider=MockProvider(mode="success", delay_seconds=0.01))
    t1 = time.perf_counter()
    await client_success.get_decision_suggestion(sample_envelope, "yes", 2)
    lat_llm_success_ms = (time.perf_counter() - t1) * 1000.0

    # 3. LLM Timeout path
    client_timeout = LLMClient(provider=MockProvider(mode="timeout"), timeout_ms=200)
    t2 = time.perf_counter()
    await client_timeout.get_decision_suggestion(sample_envelope, "yes", 2)
    lat_llm_timeout_ms = (time.perf_counter() - t2) * 1000.0

    # 4. Circuit-Open path
    cb_open = CircuitBreaker(failure_threshold=1, cooldown_seconds=10.0)
    cb_open.state = CircuitState.OPEN
    cb_open.last_failure_time = time.time()
    client_open = LLMClient(provider=MockProvider(mode="success"), circuit_breaker=cb_open)
    t3 = time.perf_counter()
    await client_open.get_decision_suggestion(sample_envelope, "yes", 2)
    lat_circuit_open_ms = (time.perf_counter() - t3) * 1000.0

    print(
        f"\nLATENCY BENCHMARK RESULTS:\n"
        f"  - Deterministic Path:  {lat_deterministic_ms:.3f}ms\n"
        f"  - LLM Success Path:    {lat_llm_success_ms:.3f}ms\n"
        f"  - LLM Timeout Path:    {lat_llm_timeout_ms:.3f}ms (bounded <= 300ms)\n"
        f"  - Circuit-Open Path:   {lat_circuit_open_ms:.3f}ms (fail-fast)\n"
    )

    assert lat_deterministic_ms < 5.0
    assert lat_circuit_open_ms < 5.0
    assert lat_llm_timeout_ms < 400.0
