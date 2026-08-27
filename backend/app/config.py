"""
Configuration and Vera Principles for magicpin AI Challenge.

IMPORTANT VERA RULES:
1. Ground everything in received context.
2. Never invent numbers, offers, dates, customer facts, or claims.
3. Handle category + merchant + trigger correctly.
4. Decide before writing.
5. Specificity is more important than generic AI copy.
6. Merchant fit is more important than generic personalization.
7. One strong CTA per message.
8. Sometimes the correct decision is wait, suppress, or end.
9. Never repeat messages or ignore suppression.
10. If the merchant clearly says YES / GO AHEAD, execute rather than continuing to qualify unnecessarily.
11. Repeated auto-replies must eventually cause backoff/end behavior.
12. Hostile or opt-out responses must stop outreach.
13. Customer outreach must respect the supplied customer context and consent.
14. New context versions must replace stale context correctly.
15. Same input should produce deterministic behavior.
16. Keep responses fast.
17. The real judge will inject unseen context, so never hardcode the sample scenarios.
18. Build small and deterministic before adding sophistication.
"""

import os
import time
from typing import List

# Database Configuration
DATABASE_PATH: str = os.getenv("DB_PATH") or os.getenv("DATABASE_PATH", "magicpin_vera.db")

# Service Metadata Configuration
APP_NAME: str = "magicpin Vera AI Backend"
APP_VERSION: str = "0.1.0"
TEAM_NAME: str = os.getenv("TEAM_NAME", "Team Vera Alpha")
TEAM_MEMBERS: List[str] = [m.strip() for m in os.getenv("TEAM_MEMBERS", "Vera Engineer").split(",")]
MODEL_NAME: str = os.getenv("MODEL_NAME", "deterministic-phase1")
APPROACH: str = "Context-grounded deterministic state engine"
CONTACT_EMAIL: str = os.getenv("CONTACT_EMAIL", "vera-team@magicpin.in")
SUBMITTED_AT: str = os.getenv("SUBMITTED_AT", "2026-08-25T00:00:00Z")

# LLM Engine Configuration
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
LLM_API_KEY: str = (
    os.getenv("GROQ_API_KEY")
    or os.getenv("LLM_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or ""
)
LLM_MODEL: str = os.getenv("GROQ_MODEL") or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TIMEOUT_MS: int = int(os.getenv("LLM_TIMEOUT_MS", "1500"))
LLM_CIRCUIT_FAILURE_THRESHOLD: int = int(os.getenv("LLM_CIRCUIT_FAILURE_THRESHOLD", "3"))
LLM_CIRCUIT_COOLDOWN_SECONDS: float = float(os.getenv("LLM_CIRCUIT_COOLDOWN_SECONDS", "10.0"))

# Observability & Trace Configuration
def is_debug_trace_enabled() -> bool:
    return os.getenv("VERA_DEBUG_TRACE", "0").lower() in ("1", "true", "yes")

VERA_DEBUG_TRACE: bool = is_debug_trace_enabled()

# Server Start Time for Uptime Calculation
START_TIME: float = time.time()
