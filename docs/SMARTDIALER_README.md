# SmartDialer — Setup & Operations Guide

## What Is SmartDialer?

SmartDialer is a **Progressive and Predictive outbound dialing engine** built as a separate module inside the CredResolve monolith. It manages the full lifecycle of outbound debt-collection calls: campaign configuration, agent allocation, pacing, safety enforcement, provider interaction, event processing, and failure recovery.

It is **architecturally separate** from the existing collections CRM, work-queue, and borrower-prioritization features. Those features are not SmartDialer implementations.

---

## Architecture Summary

```
Campaign (DialerSession)
        │
        ▼
┌──────────────────┐
│   Pacing Engine   │  Recommends how many calls to place
│  (pacing_engine)  │  (NEVER places calls directly)
└────────┬─────────┘
         │  PacingDecision
         ▼
┌──────────────────────┐
│  Safety Controller    │  Reads DB independently, approves /
│ (safety_controller)   │  reduces / rejects / fails closed
└────────┬─────────────┘
         │  SafetyDecision (approved_dials)
         ▼
┌──────────────────┐
│  Call Allocator   │  Atomically reserves agent + borrower,
│ (call_allocator)  │  selects provider, initiates call
└───────┬──────────┘
        │
   ┌────┴────┐
   ▼         ▼
Provider A  Provider B
(reliable)  (unreliable / OOO / dups)
        │
        ▼
┌──────────────────────┐
│   Event Processor     │  Deduplicates webhook events,
│ (event_processor)     │  drives call state machine
└──────────────────────┘
```

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ (3.12 used in development) |
| pip | any recent |
| SQLite | bundled with Python (no install needed) |
| Node.js | 18+ (only for frontend) |

---

## Quick Start

### 1. Install backend dependencies

```powershell
cd backend
python -m pip install -r requirements.txt
```

`requirements.txt` already includes: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic-settings`, `python-jose[cryptography]`, `bcrypt`, `pytest`, `httpx`.

### 2. Environment configuration

No mandatory environment variables for local development. Defaults:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///credresolve.db` | SQLAlchemy database URL |
| `SECRET_KEY` | `credresolve-dev-only-secret-key-change-in-production` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 h) | JWT token lifetime |

For production, create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/credresolve
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
```

### 3. Database initialization

Tables are created **automatically** on first startup. No migration tool is required. The startup sequence:

1. `Base.metadata.create_all(bind=engine)` — creates all 26 tables (19 existing + 7 SmartDialer).
2. `recover_stale_state(db)` — reconciles any stale reservations from a previous crash.

To verify tables were created:
```powershell
python -c "
from sqlalchemy import create_engine, inspect
from app.models import schema, dialer_schema
from app.core.database import Base, engine
Base.metadata.create_all(bind=engine)
print(inspect(engine).get_table_names())
"
```

### 4. Start the backend server

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

Health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 5. Start the frontend (optional)

```powershell
cd frontend
npm install
npm run dev
```

Opens at [http://localhost:5173](http://localhost:5173). Navigate to **SmartDialer Engine** in the sidebar.

---

## API Usage

### Authenticate first

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@credresolve.com&password=credresolve123"
```

Use the returned `access_token` as `Bearer` in subsequent requests.

### Create a dialing session

```bash
curl -X POST http://localhost:8000/api/v1/dialer/sessions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"mode": "PREDICTIVE", "max_dial_rate": 1.2}'
```

### Add agents to session

```bash
curl -X POST http://localhost:8000/api/v1/dialer/sessions/<session_id>/agents \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"agent_ids": ["agent-001", "agent-002", "agent-003"]}'
```

### Start dialing

```bash
curl -X POST http://localhost:8000/api/v1/dialer/sessions/<session_id>/start \
  -H "Authorization: Bearer <token>"
```

### Get pacing recommendation (read-only)

```bash
curl http://localhost:8000/api/v1/dialer/sessions/<session_id>/pacing \
  -H "Authorization: Bearer <token>"
```

Returns both the pacing engine recommendation and the Safety Controller decision.

### Run simulation (no real calls)

```bash
curl -X POST http://localhost:8000/api/v1/dialer/simulate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "B", "num_agents": 10, "num_borrowers": 100, "duration_ticks": 20, "mode": "PREDICTIVE"}'
```

Scenarios: `A` (20% answer rate), `B` (50%), `C` (70%), `D` (dynamic).

### Get provider health

```bash
curl http://localhost:8000/api/v1/dialer/providers/health
```

### Inject a provider webhook event (testing)

```bash
curl -X POST http://localhost:8000/api/v1/dialer/events \
  -H "Content-Type: application/json" \
  -d '{"call_id": "<call_id>", "provider_call_id": "PA-abc123", "event_type": "ANSWERED", "event_seq": 2}'
```

### Trigger crash recovery (ops)

```bash
curl -X POST http://localhost:8000/api/v1/dialer/recover \
  -H "Authorization: Bearer <token>"
```

---

## Running Tests

### SmartDialer test suite (44 tests)

```powershell
cd backend
python -m pytest tests/test_dialer.py -v
```

Expected output: `44 passed`

### Run specific test classes

```powershell
# Safety Controller only
python -m pytest tests/test_dialer.py::TestSafetyController -v

# Concurrency / OCC reservation race
python -m pytest tests/test_dialer.py::TestConcurrentReservation -v

# Crash recovery
python -m pytest tests/test_dialer.py::TestCrashRecovery -v

# Duplicate / OOO events
python -m pytest tests/test_dialer.py::TestEventProcessor -v
```

### Full existing test suite (includes collections platform)

```powershell
python -m pytest tests/ -v
```

---

## Running Simulations

### Via Python directly

```powershell
cd backend
python -c "
from app.services.simulation import run_scenario
import json
result = run_scenario('B', num_agents=20, num_borrowers=500, duration_ticks=30, mode='PREDICTIVE')
print(json.dumps(result['summary'], indent=2))
"
```

### Via load test script

```powershell
cd backend
python load_test.py --scenario B --agents 50 --ticks 40
python load_test.py --all-scenarios
```

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/dialer/simulate \
  -H "Authorization: Bearer <token>" \
  -d '{"scenario":"D","num_agents":50,"num_borrowers":500,"duration_ticks":30,"mode":"PREDICTIVE"}'
```

---

## Key Design Decisions (summary)

| Decision | Choice | Reason |
|---|---|---|
| Architecture | Modular monolith | Avoids distributed-systems overhead; SQLite locks are sufficient for the assignment scope |
| Database locking | Optimistic concurrency control (OCC) via `UPDATE WHERE version=N` | Works on SQLite; upgrades transparently to PostgreSQL `SELECT FOR UPDATE` |
| State machine | Explicit transition table, enforced at DB level | Prevents invalid states; idempotent on terminal states |
| Safety isolation | SafetyController reads DB directly, never trusts pacing input | Pacing engine has no code path to bypass it |
| Event idempotency | Unique constraint on `(call_id, event_type, event_seq)` | Duplicate events rejected at DB level, not just in-memory |
| Crash recovery | TTL-based stale scan on startup | Simple, correct; no heartbeat infrastructure needed |
| Provider interface | Abstract `TelecomProvider` class | Dialer never imports concrete providers |

See [architecture_adr.md](docs/architecture_adr.md) for full rationale.

---

## Known Limitations

1. **SQLite concurrency**: WAL mode serializes writes. Throughput ceiling is ~1,000 reservations/second on commodity hardware. Switch to PostgreSQL for production (change `DATABASE_URL`; code is compatible).

2. **No true `SELECT FOR UPDATE`**: SQLite does not support `SKIP LOCKED`. The OCC `UPDATE WHERE (state='AVAILABLE' AND version=N)` achieves the same safety guarantee for serialized writes.

3. **Mock providers only**: `ProviderAlpha` and `ProviderBeta` are in-process simulations. No real telecom credentials are required or used.

4. **No Kafka / Redis**: Webhook events are delivered synchronously via Python callback. In production, these would arrive via HTTP from a real provider; the `POST /dialer/events` endpoint handles that path.

5. **Load test scope**: The load test script measures local in-process throughput. It does not simulate 10,000 simultaneous real network connections.

6. **Frontend TypeScript**: Not compiled during CI because `node_modules` is not committed. Run `npm install && npm run build` to verify.

---

## Final Question — Predictive Utilization with Progressive Safety

> *"How would you combine the high agent utilization of predictive dialing with the safety guarantee of progressive dialing?"*

See [docs/architecture_adr.md — Final Question](docs/architecture_adr.md#final-question) for the full answer.

**Short answer**: The Safety Controller already implements this hybrid. It evaluates the pacing engine's predictive recommendation but revalidates capacity from the database at the atomic reservation boundary. If any condition that would create an abandoned call exists (no available agents, overhang ratio exceeded, circuit open), it falls back to the progressive cap (1 call per available agent). This means the system dials predictively when it is safe to do so, and degrades gracefully to progressive when it is not — without requiring explicit mode switching.
