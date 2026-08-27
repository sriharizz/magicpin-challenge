"""
Provider Implementations and Neutral Interface for Vera's LLM Engine.

Defines:
1. LLMProvider (Abstract Base Class)
2. MockProvider (Deterministic, programmable mock for unit/integration/adversarial testing)
3. GeminiProvider (Google Gemini REST API adapter with strict JSON output)
4. OpenAIProvider (OpenAI REST API adapter with strict JSON output)
"""

import abc
import asyncio
import json
import logging
from typing import Optional, Dict, Any

import httpx
from app.llm.schemas import LLMContextEnvelope, LLMDecisionSuggestion
from app.llm.prompts import SYSTEM_PROMPT, format_user_prompt

logger = logging.getLogger("vera.llm.provider")


class LLMProvider(abc.ABC):
    """Abstract interface for all LLM providers."""

    @abc.abstractmethod
    def name(self) -> str:
        """Return provider identifier name."""
        pass

    @abc.abstractmethod
    async def generate(
        self,
        envelope: LLMContextEnvelope,
        user_message: str,
        turn_number: int,
        timeout_seconds: float = 1.5,
    ) -> Optional[LLMDecisionSuggestion]:
        """Generate structured LLM decision suggestion."""
        pass


class MockProvider(LLMProvider):
    """
    Programmable mock provider for offline testing and adversarial test harnesses.
    Supports simulating timeouts, network errors, malformed outputs, and custom suggestions.
    """

    def __init__(
        self,
        mode: str = "success",
        custom_suggestion: Optional[LLMDecisionSuggestion] = None,
        delay_seconds: float = 0.0,
    ):
        self.mode = mode
        self.custom_suggestion = custom_suggestion
        self.delay_seconds = delay_seconds
        self.call_count = 0

    def name(self) -> str:
        return f"MockProvider(mode={self.mode})"

    def set_mode(self, mode: str, custom_suggestion: Optional[LLMDecisionSuggestion] = None):
        self.mode = mode
        self.custom_suggestion = custom_suggestion

    async def generate(
        self,
        envelope: LLMContextEnvelope,
        user_message: str,
        turn_number: int,
        timeout_seconds: float = 1.5,
    ) -> Optional[LLMDecisionSuggestion]:
        self.call_count += 1

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.mode == "timeout":
            # Sleep longer than the client timeout budget
            await asyncio.sleep(timeout_seconds + 0.5)
            return None

        if self.mode == "network_error":
            raise httpx.ConnectError("Simulated network connection failure")

        if self.mode == "http_429":
            raise httpx.HTTPStatusError("HTTP 429 Too Many Requests", request=None, response=None)

        if self.mode == "http_500":
            raise httpx.HTTPStatusError("HTTP 500 Internal Server Error", request=None, response=None)

        if self.mode == "malformed_json":
            raise ValueError("Malformed JSON payload returned from upstream model")

        if self.mode == "invalid_schema":
            # Return None to simulate unparseable schema
            return None

        if self.custom_suggestion:
            return self.custom_suggestion

        # Context-aware mock generation strictly grounded in envelope facts
        clean_msg = user_message.strip().lower()
        trial_n_fact = next((f for f in envelope.supported_facts if "trial_n" in f.key or f.key == "trial_n"), None)
        cited_facts = []

        if any(q in clean_msg for q in ("sample size", "how many", "patient count", "trial size")):
            if trial_n_fact:
                body_text = (
                    f"The clinical trial evaluated {trial_n_fact.value} patients for secondary root caries prevention. "
                    f"Next step: want me to prepare the patient draft?"
                )
                cited_facts = [trial_n_fact.fact_id]
                unknown_facts = []
            else:
                body_text = (
                    "The available digest summary does not specify the exact patient sample size for this item. "
                    "Would you like me to share the clinical abstract and key takeaways?"
                )
                unknown_facts = ["trial_sample_size"]

            return LLMDecisionSuggestion(
                suggested_intent="INTENT_QUESTION",
                confidence=0.96,
                proposed_action="send",
                response_strategy="factual_question_answering",
                draft_body=body_text,
                proposed_cta="binary_yes_no",
                cited_fact_ids=cited_facts,
                unknown_facts_requested=unknown_facts,
                rationale="Grounded answer to factual query using supported facts table.",
            )

        if any(
            u in clean_msg
            for u in (
                "not sure",
                "not ready",
                "never mind",
                "sure?",
                "yes?",
                "okay?",
                "maybe",
                "tell me more",
                "what is this",
                "sure...",
                "yes?!",
            )
        ):
            return LLMDecisionSuggestion(
                suggested_intent="INTENT_UNKNOWN",
                confidence=0.90,
                proposed_action="send",
                response_strategy="clarify_low_friction",
                draft_body=(
                    "Happy to clarify: this is a concise 2-minute overview of recent clinical findings. "
                    "Would you like to review the 1-page clinical abstract or the patient WhatsApp draft?"
                ),
                proposed_cta="binary_yes_no",
                cited_fact_ids=[],
                unknown_facts_requested=[],
                rationale="Clarified low-friction binary choice without assuming commitment.",
            )

        # Default affirmative delivery
        cited_facts = [f.fact_id for f in envelope.supported_facts[:2]]
        body_text = (
            "Sending the abstract summary now. I have also prepared a patient draft: "
            "Recent clinical trial confirms significant caries reduction (n=2,100). "
            "Next step: want me to prepare the follow-up recall template?"
        )
        return LLMDecisionSuggestion(
            suggested_intent="INTENT_AFFIRM",
            confidence=0.98,
            proposed_action="send",
            response_strategy="deliver_abstract_and_draft",
            draft_body=body_text,
            proposed_cta="binary_yes_no",
            cited_fact_ids=cited_facts,
            unknown_facts_requested=[],
            rationale="Mock provider generated verified context-grounded action response.",
        )


class GeminiProvider(LLMProvider):
    """Google Gemini REST API adapter with native JSON schema enforcement."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model or "gemini-2.5-flash"

    def name(self) -> str:
        return f"GeminiProvider({self.model})"

    async def generate(
        self,
        envelope: LLMContextEnvelope,
        user_message: str,
        turn_number: int,
        timeout_seconds: float = 1.5,
    ) -> Optional[LLMDecisionSuggestion]:
        if not self.api_key:
            logger.warning("GeminiProvider called without API key")
            return None

        user_content = format_user_prompt(envelope, user_message, turn_number)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": user_content}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
                "maxOutputTokens": 1200,
            },
        }

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            candidates = data.get("candidates", [])
            if not candidates:
                return None

            raw_text = candidates[0]["content"]["parts"][0]["text"]
            try:
                parsed_dict = json.loads(raw_text)
                return LLMDecisionSuggestion.model_validate(parsed_dict)
            except Exception as ex:
                logger.warning("Failed to parse Gemini JSON output (%s): %s", type(ex).__name__, raw_text[:100])
                return None


class OpenAIProvider(LLMProvider):
    """OpenAI REST API adapter with JSON mode."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"

    def name(self) -> str:
        return f"OpenAIProvider({self.model})"

    async def generate(
        self,
        envelope: LLMContextEnvelope,
        user_message: str,
        turn_number: int,
        timeout_seconds: float = 1.5,
    ) -> Optional[LLMDecisionSuggestion]:
        if not self.api_key:
            logger.warning("OpenAIProvider called without API key")
            return None

        user_content = format_user_prompt(envelope, user_message, turn_number)
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 800,
        }

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            choices = data.get("choices", [])
            if not choices:
                return None

            raw_text = choices[0]["message"]["content"]
            parsed_dict = json.loads(raw_text)
            return LLMDecisionSuggestion.model_validate(parsed_dict)


class GroqProvider(LLMProvider):
    """Groq REST API adapter with JSON mode and ultra-fast inference."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", base_url: str = ""):
        self.api_key = api_key
        self.model = model or "llama-3.3-70b-versatile"
        self.base_url = base_url or "https://api.groq.com/openai/v1/chat/completions"

    def name(self) -> str:
        return f"GroqProvider({self.model})"

    async def generate(
        self,
        envelope: LLMContextEnvelope,
        user_message: str,
        turn_number: int,
        timeout_seconds: float = 1.5,
    ) -> Optional[LLMDecisionSuggestion]:
        if not self.api_key:
            logger.warning("GroqProvider called without API key; falling back to deterministic engine")
            return None

        user_content = format_user_prompt(envelope, user_message, turn_number)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 800,
        }

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(self.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            choices = data.get("choices", [])
            if not choices:
                return None

            raw_text = choices[0]["message"]["content"]
            parsed_dict = json.loads(raw_text)
            return LLMDecisionSuggestion.model_validate(parsed_dict)

