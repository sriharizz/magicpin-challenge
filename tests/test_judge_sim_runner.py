"""
Execution of judge_simulator scenarios against our FastAPI backend.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add challenge directory to sys.path
CHALLENGE_DIR = Path(__file__).parent.parent / "magicpin-ai-challenge"
sys.path.insert(0, str(CHALLENGE_DIR))

from judge_simulator import DatasetLoader, ScoreResult, LLMScorer, DATASET_DIR, JudgeSimulator, LLMProvider
from app.main import app


class _ClientBotAdapter:
    """Adapts FastAPI TestClient to mimic BotClient in judge_simulator."""
    def __init__(self, client: TestClient):
        self.client = client

    def healthz(self):
        res = self.client.get("/v1/healthz")
        return res.json(), None, 2.0

    def metadata(self):
        res = self.client.get("/v1/metadata")
        return res.json(), None, 1.5

    def push_context(self, scope, cid, version, payload):
        res = self.client.post("/v1/context", json={
            "scope": scope, "context_id": cid, "version": version,
            "payload": payload, "delivered_at": "2026-04-26T10:00:00Z"
        })
        return res.json(), None, 3.0

    def tick(self, triggers):
        res = self.client.post("/v1/tick", json={
            "now": "2026-04-26T10:35:00Z", "available_triggers": triggers
        })
        return res.json(), None, 4.0

    def reply(self, conv_id, merchant_id, message, turn):
        res = self.client.post("/v1/reply", json={
            "conversation_id": conv_id, "merchant_id": merchant_id, "customer_id": None,
            "from_role": "merchant", "message": message,
            "received_at": "2026-04-26T10:35:00Z", "turn_number": turn
        })
        return res.json(), None, 2.0


class _MockJudgeLLM(LLMProvider):
    """Mock LLM Provider for offline judge simulation execution."""
    def name(self) -> str:
        return "MockJudgeLLM"

    def complete(self, prompt: str, system: str = None) -> str:
        return '{"specificity": 9, "category_fit": 9, "merchant_fit": 9, "decision_quality": 9, "engagement_compulsion": 9, "penalties": 0, "penalty_reasons": [], "hint": "Excellent composition"}'


def test_judge_simulator_warmup_and_phase2_short(client: TestClient):
    """Run the exact warmup and phase2_short scenarios from judge_simulator.py."""
    adapter = _ClientBotAdapter(client)
    dataset = DatasetLoader(DATASET_DIR)
    assert dataset.load() is True

    # 1. Warmup
    data, err, _ = adapter.healthz()
    assert err is None
    assert "status" in data

    data, err, _ = adapter.metadata()
    assert err is None
    assert "team_name" in data

    # Push categories
    for slug, cat in dataset.categories.items():
        data, err, _ = adapter.push_context("category", slug, 1, cat)
        assert data.get("accepted") is True

    # Push merchants
    for mid, m in list(dataset.merchants.items())[:5]:
        data, err, _ = adapter.push_context("merchant", mid, 1, m)
        assert data.get("accepted") is True

    # 2. Phase 2 Short (Tick Test)
    trigs = list(dataset.triggers.keys())[:3]
    for tid in trigs:
        data, err, _ = adapter.push_context("trigger", tid, 1, dataset.triggers[tid])
        assert data.get("accepted") is True

    data, err, lat = adapter.tick(trigs)
    assert err is None
    actions = data.get("actions", [])
    assert isinstance(actions, list)

    for action in actions:
        body = action.get("body", "")
        assert len(body) > 10
        assert action.get("cta") in ("open_ended", "quick_reply", "calendar", "none", "binary_yes_no")
        assert action.get("send_as") in ("vera", "magicpin", "merchant")


def test_judge_simulator_scenarios_all(client: TestClient):
    """Run judge_simulator's auto_reply, intent, and hostile scenarios directly."""
    sim = JudgeSimulator(_MockJudgeLLM())
    sim.client = _ClientBotAdapter(client)
    assert sim.dataset.load() is True

    # Run Warmup first to seed context
    assert sim._warmup() is True

    # Run auto_reply scenario
    assert sim._auto_reply() is True

    # Run intent transition scenario
    assert sim._intent() is True

    # Run hostile scenario
    assert sim._hostile() is True
