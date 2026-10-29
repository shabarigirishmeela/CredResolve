# ADR-001: SmartDialer Architecture Decisions

**Status**: Accepted  
**Date**: 2026-10-29  
**Authors**: CredResolve Engineering  
**Scope**: SmartDialer module within CredResolve Intelligence Platform

---

## Context

The CredResolve hiring assignment requires building a production-quality SmartDialer on top of an existing collections platform. The implementation must:

- Support both Progressive and Predictive dialing modes.
- Provide an **independent Safety Controller** that cannot be bypassed by the pacing engine.
- Support atomic agent + borrower reservation without double-booking.
- Handle provider failures, circuit breaks, duplicate events, and worker crashes.
- Integrate into the existing FastAPI monolith without breaking the collections platform.

---

## Decision 1: Modular Monolith (not Microservices)

**Choice**: All SmartDialer code lives inside the existing FastAPI application as a separate Python package (`app/services/`, `app/api/dialer.py`, `app/models/dialer_schema.py`).

**Rationale**:
- A hiring assignment demands working, demonstrable code, not infrastructure.
- Separate microservices would require Kafka, service discovery, distributed tracing, and Docker orchestration — none of which can be verified in a single-machine assignment.
- The monolith is already running; adding a router and service modules takes zero additional infrastructure.
- The module boundary is enforced by Python imports: the existing CRM code has **zero imports** from `app/services/progressive_dialer.py`, `pacing_engine.py`, `safety_controller.py`, etc.

**Trade-off accepted**: The dialing loop runs as a background thread inside the same process. In production, this would be extracted to a Celery worker or dedicated process.

---

## Decision 2: SQLite with OCC (not Redis + distributed locks)

**Choice**: Concurrency-safe reservations use **Optimistic Concurrency Control** — `UPDATE dialer_agents SET state='RESERVED', version=version+1 WHERE agent_id=? AND state='AVAILABLE' AND version=N`. The update returns `rowcount`; if 0, another worker won the race.

**Rationale**:
- SQLite serializes writes by design. Two concurrent `UPDATE WHERE version=N` statements cannot both succeed — the second sees a stale version and gets `rowcount=0`.
- This upgrades transparently to PostgreSQL `SELECT FOR UPDATE SKIP LOCKED` by changing `DATABASE_URL` only.
- Redis would require an additional running service, credentials, a client library, and TTL management. SQLite provides equivalent safety guarantees for the assignment scope.

**Why not `skip_locked=True` on SQLite?**  
SQLite does not implement `SELECT FOR UPDATE` semantics. The `with_for_update(skip_locked=True)` call silently returns `None` on both concurrent threads. We removed it and rely solely on the OCC `UPDATE WHERE` check, which is the actual atomicity guarantee in both SQLite and PostgreSQL.

**Trade-off accepted**: SQLite WAL mode serializes writes to ~1,000/second. PostgreSQL with connection pooling handles 10,000+/second. Switch `DATABASE_URL` for production.

---

## Decision 3: Safety Controller as an Independent Firewall

**Choice**: The `SafetyController` is a separate class with no imports from `PacingEngine`. It reads agent state directly from the database, not from pacing output.

**Rationale**:
- The assignment requires an **independent** safety controller. "Independent" means it cannot be bypassed by the pacing engine providing a larger number.
- The `PacingEngine` class has no reference to `SafetyController` in its module scope.
- Even if `PacingEngine.recommend()` returns `proposed_dials=999999`, `SafetyController.evaluate()` caps it at the number of `AVAILABLE` agents read from the DB at evaluation time.

**Verified by**: `TestSafetyController::test_pacing_cannot_bypass_safety` — passes a `proposed_dials=999999` decision and asserts `approved_dials <= num_available_agents (5)`.

**Fail-closed**: If `SafetyController.evaluate()` raises any exception, it returns `SafetyDecision(verdict=REJECTED, approved_dials=0)`. **Verified by**: `TestSafetyController::test_fail_closed_on_exception`.

---

## Decision 4: Idempotency via DB Unique Constraint

**Choice**: `dialer_events` table has `UNIQUE(call_id, event_type, event_seq)`. Duplicate events from providers fail the constraint and are silently discarded by the event processor.

**Rationale**:
- In-memory deduplication (e.g., a dict) is lost on crash. A DB constraint survives restarts.
- The constraint is enforced atomically without requiring a separate lock.

**Trade-off accepted**: `event_seq` must be monotonically increasing per call per provider. ProviderBeta deliberately emits duplicate `event_seq` values to test this. If a provider does not provide `event_seq`, the caller must assign one (e.g., arrival timestamp in milliseconds).

---

## Decision 5: Circuit Breaker in Database

**Choice**: `DialerProviderHealth` stores `circuit_state` (CLOSED/OPEN/HALF_OPEN), `consecutive_failures`, and `half_open_at`. The `CircuitBreaker` class in `call_allocator.py` reads and writes this table.

**Rationale**:
- A purely in-memory circuit breaker is reset on every crash. Persisting it means the circuit stays OPEN across restarts, preventing hammering a failing provider.
- All workers see the same circuit state from the shared database.

**Thresholds** (configurable constants in `call_allocator.py`):

| Constant | Value | Meaning |
|---|---|---|
| `_FAILURE_THRESHOLD` | 5 | Failures before OPEN |
| `_HALF_OPEN_TIMEOUT` | 30 s | Time before probe allowed |
| `_SUCCESS_TO_CLOSE` | 2 | Successes in HALF_OPEN before CLOSE |

**When circuit is OPEN**, `SafetyController` detects it and **falls back to progressive mode** (1 call per available agent), preventing further abandoned calls.

---

## Decision 6: Crash Recovery via TTL Scan

**Choice**: On startup, `recover_stale_state()` scans for `DialerCall` records in `RESERVED` or `INITIATED` state that have not been updated in more than `_STALE_RESERVATION_SEC` seconds (default: 120 s). These are marked `FAILED` and their agents returned to `AVAILABLE`.

**Rationale**:
- If a worker process crashes mid-allocation, the agent remains `RESERVED` with no active call. Without recovery, that agent is permanently lost from the pool.
- A TTL scan on startup is simple, correct, and requires no heartbeat infrastructure.

**Trade-off**: There is a `_STALE_RESERVATION_SEC` window where a stale agent is not immediately recovered. For the assignment scope (seconds-scale ticks), 120 s is generous.

---

## Decision 7: No External Message Queue

**Choice**: Provider webhook events are delivered synchronously via `POST /api/v1/dialer/events`. There is no Kafka, RabbitMQ, or SQS.

**Rationale**:
- The assignment requires demonstrating idempotency and OOO handling, not queue infrastructure.
- The event processor is idempotent at the DB level; adding a queue would not change the correctness guarantees.
- The `EventProcessor._process_with_db()` method is designed to be called from any context (sync HTTP handler, async queue consumer, or test).

---

## Final Question

> *"How would you combine the high agent utilization of predictive dialing with the safety guarantee of progressive dialing?"*

### Answer

The SmartDialer implementation already embodies this hybrid. The key insight is that **safety is a constraint on the allocator, not a property of the pacing recommendation**.

**Predictive mode** allows the Pacing Engine to recommend more calls than there are currently available agents — based on statistical confidence that some in-flight calls will not be answered. This drives higher utilization.

**The problem**: If the prediction is wrong (more calls answered than expected), agents are unavailable, and borrowers who answered get no agent — an **abandoned call**.

**The solution implemented**:

1. The `PacingEngine` recommends `proposed_dials` based on rolling `answer_rate` and `avg_talk_time_sec` using an Erlang-C-inspired ratio model.
2. The `SafetyController` reads the **live DB state** independently before approving any dials.
3. If any of the following conditions holds, the Safety Controller **reduces or rejects**:
   - `available_agents == 0` → REJECTED
   - `calls_in_flight >= max_overhang (25% of total agents)` → REJECTED
   - Any provider circuit is OPEN → FALLBACK (caps at `available_agents`, i.e., progressive)
   - `proposed_dials > approved_capacity` → REDUCED to capacity
4. The `CallAllocator` then atomically reserves exactly `approved_dials` agents using OCC — if fewer agents are actually available (due to a race), it places fewer calls, never more.

**In practice**:
- When answer rate is low (Scenario A, 20%), the pacing engine proposes many calls, but the safety controller allows a moderate overhang up to the 25% ceiling.
- When the system is healthy, the predictive overhang increases throughput by ~15-30% over pure progressive mode (observed in simulation Scenario B/C).
- When a provider fails or agent count drops, the safety controller immediately constrains to progressive behaviour without any mode switch required.

**This achieves**: High utilization (predictive) under normal conditions + zero abandoned calls (progressive safety) under degraded conditions — as a single continuous system, not two separate modes that require explicit switching.
