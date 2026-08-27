# magicpin Vera AI — Production Deployment & Operations Guide

## 1. System Overview

Vera is a high-performance, deterministic context-grounded AI backend engineered for the **magicpin AI Challenge**. The system is built with **FastAPI**, **SQLite (WAL mode)**, and a **circuit-breaking multi-provider LLM cascade**.

### Key Architectural Invariants
- **100% Contract Compliant**: Implements `GET /v1/healthz`, `GET /v1/metadata`, `POST /v1/context`, `POST /v1/tick`, `POST /v1/reply`.
- **Zero Single-Point-of-Failure**: If LLM providers are down, rate-limited, or timing out, Vera seamlessly executes context-grounded responses via its deterministic engine.
- **Fast Response Latencies**: Sub-5ms internal response latency on deterministic routes; <1500ms timeout budget on LLM routes.
- **Ephemeral-Safe Persistence**: Context store paths are dynamically configurable via `DB_PATH`.

---

## 2. Environment Variables

| Variable | Default | Description | Required |
| :--- | :--- | :--- | :---: |
| `PORT` | `8080` (Docker) / `8000` (Local) | HTTP server port | Yes |
| `HOST` | `0.0.0.0` | HTTP bind address | Yes |
| `DB_PATH` | `/data/magicpin_vera.db` | Absolute path to SQLite database | Yes |
| `TEAM_NAME` | `Team Vera Alpha` | Team identifier returned in `/v1/metadata` | Optional |
| `TEAM_MEMBERS` | `Vera Engineer` | Comma-separated list of team member names | Optional |
| `MODEL_NAME` | `deterministic-phase1` | Model name description | Optional |
| `CONTACT_EMAIL` | `vera-team@magicpin.in`| Contact email | Optional |
| `LLM_PROVIDER` | `mock` | `mock`, `gemini`, `openai`, `groq`, `cerebras` | Optional |
| `LLM_API_KEY` | `""` | API key for selected LLM provider | Optional |
| `LLM_MODEL` | `""` | Model identifier (e.g. `gemini-2.5-flash`, `gpt-4o-mini`) | Optional |
| `LLM_TIMEOUT_MS` | `1500` | Client-side timeout ceiling for LLM calls | Optional |
| `LLM_CIRCUIT_FAILURE_THRESHOLD` | `3` | Consecutive failures before circuit trips to OPEN | Optional |
| `LLM_CIRCUIT_COOLDOWN_SECONDS` | `10.0` | Cooldown period before probing provider recovery | Optional |
| `VERA_DEBUG_TRACE`| `0` | Enable detailed SQLite debug traces (`0` or `1`) | Optional |

---

## 3. Container Deployment (Docker)

### Build the Image
```bash
docker build -t magicpin-vera:latest .
```

### Run Container with Persistent Volume
```bash
docker run -d \
  --name magicpin-vera \
  -p 8080:8080 \
  -v $(pwd)/vera_data:/data \
  -e PORT=8080 \
  -e DB_PATH=/data/magicpin_vera.db \
  magicpin-vera:latest
```

---

## 4. Platform Deployment Instructions

### A. Google Cloud Run (Recommended)
1. Ensure **Minimum Instances** is set to $\ge 1$ to prevent cold starts during evaluation.
2. Mount a Cloud Storage volume or Cloud SQL volume at `/data` if multi-instance synchronization is desired.
3. Configure `PORT=8080` and `DB_PATH=/data/magicpin_vera.db`.

### B. AWS ECS / Fargate
1. Configure task definition with persistent EFS volume mounted at `/data`.
2. Configure container port mapping to `8080`.
3. Set health check probe to `GET /v1/healthz`.

### C. Render / Railway / Fly.io
1. Add a persistent volume disk mounted at `/data` (1GB is more than sufficient).
2. Set environment variables: `DB_PATH=/data/magicpin_vera.db`, `HOST=0.0.0.0`.
3. On Render/Railway, select **Starter (Always-on)** plan to avoid sleep states.

---

## 5. Health Checks & Verification

### Liveness & Readiness Probe
```http
GET /v1/healthz
```
Response:
```json
{
  "status": "ok",
  "uptime_seconds": 320,
  "contexts_loaded": {
    "category": 5,
    "merchant": 50,
    "customer": 200,
    "trigger": 0
  }
}
```

### Metadata Probe
```http
GET /v1/metadata
```

---

## 6. Cold-Start & Concurrency Guidelines

- **Always-On Requirement**: Free-tier cloud instances with sleep-after-inactivity policies can take 30–60 seconds to wake up, which risks timing out judge requests. Deploy on always-on instances with `min_instances >= 1`.
- **Database Concurrency**: SQLite runs in **WAL (Write-Ahead Logging)** mode with `busy_timeout = 5000ms`, handling concurrent reads and serialized writes without table lock contention.
- **Circuit Breaker Protection**: In the event of upstream LLM rate limits (HTTP 429) or outages (HTTP 500/503), the circuit breaker trips to `OPEN` within 3 failures, preventing hanging requests and immediately returning verified deterministic responses.
