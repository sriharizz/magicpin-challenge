# magicpin Vera AI Challenge — Backend

A deterministic, context-grounded AI engine backend built for the **magicpin Vera AI Challenge**.

---

## 📌 Core Vera Rules (Mandatory Operational Invariants)

1. **Ground everything in received context.**
2. **Never invent numbers, offers, dates, customer facts, or claims.**
3. **Handle category + merchant + trigger correctly.**
4. **Decide before writing.**
5. **Specificity is more important than generic AI copy.**
6. **Merchant fit is more important than generic personalization.**
7. **One strong CTA per message.**
8. **Sometimes the correct decision is wait, suppress, or end.**
9. **Never repeat messages or ignore suppression.**
10. **If the merchant clearly says YES / GO AHEAD, execute rather than continuing to qualify unnecessarily.**
11. **Repeated auto-replies must eventually cause backoff/end behavior.**
12. **Hostile or opt-out responses must stop outreach.**
13. **Customer outreach must respect the supplied customer context and consent.**
14. **New context versions must replace stale context correctly.**
15. **Same input should produce deterministic behavior.**
16. **Keep responses fast (< 30s deadline; < 50ms local context processing).**
17. **The real judge will inject unseen context, so never hardcode the sample scenarios.**
18. **Build small and deterministic before adding sophistication.**

---

## 🏗️ Architecture — Phase 1 Foundation

Phase 1 provides a clean, modular foundation:
- **FastAPI HTTP Service**: Asynchronous, typed endpoints.
- **Pydantic V2 Schemas**: Strict validation for requests and responses.
- **SQLite Context Store**: Persistent, ACID-compliant storage with atomic version management.
- **Versioning Invariants**:
  - *First version*: Accepted and stored.
  - *Same version*: Idempotent no-op (accepted with existing metadata).
  - *Higher version*: Atomically replaces previous version.
  - *Lower version*: Rejected with `409 Conflict` (`stale_version`).
- **Context Scopes**: `category`, `merchant`, `customer`, `trigger`.
- **Zero Heavy Infrastructure**: No vector DBs, Redis, or unnecessary frameworks.

---

## 🚀 Running Locally

### 1. Quick Start (Single Command)

```bash
python run.py
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The server will start at `http://localhost:8080`.

### 2. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Server listening port |
| `HOST` | `0.0.0.0` | Server listening host |
| `DATABASE_PATH` | `magicpin_vera.db` | Path to SQLite database file |
| `TEAM_NAME` | `Team Vera Alpha` | Team name returned in `/v1/metadata` |
| `TEAM_MEMBERS` | `Vera Engineer` | Comma-separated list of team members |
| `MODEL_NAME` | `deterministic-phase1` | Model name identifier |

---

## 🧪 Running Tests

Run the full pytest suite:

```bash
pytest tests/ -v
```

### Test Coverage Summary
- `tests/test_context.py`:
  - Context creation across all 4 scopes (`category`, `merchant`, `customer`, `trigger`)
  - Duplicate version handling (idempotent no-op)
  - Higher version replacement (atomic update)
  - Stale version rejection (HTTP 409 `stale_version`)
  - Invalid scope rejection (HTTP 400)
- `tests/test_health.py`:
  - `GET /v1/healthz` initial zero state & uptime
  - `GET /v1/healthz` accurate count reflections across scopes
  - `GET /v1/metadata` contract compliance
- `tests/test_interaction.py`:
  - `POST /v1/tick` baseline stub
  - `POST /v1/reply` baseline stub

---

## 📡 API Contract & Examples

### 1. `GET /v1/healthz`
**Response (200 OK):**
```json
{
  "status": "ok",
  "uptime_seconds": 45,
  "contexts_loaded": {
    "category": 5,
    "merchant": 50,
    "customer": 200,
    "trigger": 0
  }
}
```

### 2. `GET /v1/metadata`
**Response (200 OK):**
```json
{
  "team_name": "Team Vera Alpha",
  "team_members": ["Vera Engineer"],
  "model": "deterministic-phase1",
  "approach": "Context-grounded deterministic state engine",
  "contact_email": "vera-team@magicpin.in",
  "version": "0.1.0",
  "submitted_at": "2026-08-25T00:00:00Z"
}
```

### 3. `POST /v1/context`
**Request Body:**
```json
{
  "scope": "merchant",
  "context_id": "m_001_drmeera",
  "version": 1,
  "payload": {
    "merchant_id": "m_001_drmeera",
    "category_slug": "dentists",
    "identity": {
      "name": "Dr. Meera's Dental Clinic",
      "city": "Delhi",
      "locality": "Lajpat Nagar"
    }
  },
  "delivered_at": "2026-04-26T10:00:00Z"
}
```
**Success Response (200 OK):**
```json
{
  "accepted": true,
  "ack_id": "ack_m_001_drmeera_v1",
  "stored_at": "2026-04-26T10:00:00.123Z"
}
```
**Stale Conflict Response (409 Conflict):**
```json
{
  "accepted": false,
  "reason": "stale_version",
  "current_version": 2
}
```

### 4. `POST /v1/tick`
**Request Body:**
```json
{
  "now": "2026-04-26T10:30:00Z",
  "available_triggers": ["trg_001_research_digest"]
}
```
**Response (200 OK):**
```json
{
  "actions": []
}
```

### 5. `POST /v1/reply`
**Request Body:**
```json
{
  "conversation_id": "conv_001",
  "merchant_id": "m_001_drmeera",
  "customer_id": null,
  "from_role": "merchant",
  "message": "Yes, tell me more",
  "received_at": "2026-04-26T10:35:00Z",
  "turn_number": 2
}
```
**Response (200 OK):**
```json
{
  "action": "end",
  "rationale": "Phase 1 baseline stub — message composition not enabled in Phase 1"
}
```

---

## 🐳 Docker Deployment

Build the container image:
```bash
docker build -t magicpin-vera-backend:latest .
```

Run container:
```bash
docker run -p 8080:8080 magicpin-vera-backend:latest
```
