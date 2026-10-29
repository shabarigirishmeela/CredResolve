# SmartDialer — Failure Recovery Reference

## 1. Worker / Process Crash

### Scenario
The Python process hosting the dialing loop crashes mid-allocation. One or more agents are left in `RESERVED` state with no active call, and `DialerCall` records are stuck in `RESERVED` or `INITIATED`.

### Detection mechanism
On every application startup, `recover_stale_state()` in `event_processor.py` scans for:
- `DialerCall.state IN ('RESERVED', 'INITIATED', 'RINGING')` with `updated_at < NOW() - 120s`

### Recovery actions
1. Mark stale calls → `FAILED`
2. Release their agents → `AVAILABLE`
3. Release borrower locks
4. Log the recovery action to `dialer_state_logs`

### Trigger manually (ops)
```bash
curl -X POST http://localhost:8000/api/v1/dialer/recover \
  -H "Authorization: Bearer <token>"
```

### Verification
Test: `TestCrashRecovery::test_stale_reserved_call_recovered` — creates a call with backdated `updated_at`, calls `recover_stale_state()`, asserts call is `FAILED` and agent is `AVAILABLE`.

### TTL window
Default: **120 seconds**. Constant `_STALE_RESERVATION_SEC` in `event_processor.py`. Fresh reservations (< 120 s old) are not touched even if the process crashed — this prevents false-positive recovery of in-flight allocations.

---

## 2. Provider Outages and Circuit Breakers

### Scenario
`ProviderBeta` (or any real provider) begins returning errors for every call initiation attempt.

### Circuit Breaker state machine
```
CLOSED  ──(5 consecutive failures)──►  OPEN
OPEN    ──(30 s timeout)─────────────►  HALF_OPEN
HALF_OPEN ──(2 successes)────────────►  CLOSED
HALF_OPEN ──(any failure)────────────►  OPEN
```

### Effect on safety
When `SafetyController` detects **any** circuit in `OPEN` state, it:
1. Sets verdict to `FALLBACK`
2. Caps `approved_dials` at `available_agents` (progressive mode)
3. This ensures no calls are placed speculatively if a provider cannot handle them

### Recovery
- After `_HALF_OPEN_TIMEOUT` (30 s), the circuit transitions to `HALF_OPEN`
- The allocator sends one probe call through the recovering provider
- Two consecutive successes close the circuit
- Any failure in `HALF_OPEN` reopens it

### Verification
Tests: `TestCircuitBreaker::test_opens_after_threshold_failures`, `test_transitions_to_half_open_after_timeout`, `test_closes_after_successes`

### Persisted state
Circuit state is stored in `dialer_provider_health`. It survives process restarts — a provider that was `OPEN` before a crash remains `OPEN` after restart.

---

## 3. Duplicate Provider Events

### Scenario
The provider network retries a webhook delivery. The `ANSWERED` event for call `C-001` arrives twice with the same `event_seq=2`.

### Detection mechanism
`dialer_events` table has:
```sql
UNIQUE (call_id, event_type, event_seq)
```

### Recovery actions
1. First event: INSERT succeeds → call state transitions to `ANSWERED`.
2. Second event: INSERT raises `IntegrityError` (UNIQUE violation).
3. `EventProcessor` catches the error, rolls back the savepoint, returns `processed=False`.
4. Call state is **not modified** — remains `ANSWERED`.

### API response
```json
{"processed": false, "reason": "duplicate_event"}
```

### Verification
Test: `TestEventProcessor::test_duplicate_answered_event_ignored`

---

## 4. Out-of-Order Provider Events

### Scenario
ProviderBeta delivers `COMPLETED` before `ANSWERED` due to network reordering. Call is currently `RINGING`.

### Detection mechanism
The call state machine in `state_machines.py` maintains an explicit **valid transitions table**. `RINGING → COMPLETED` is not a valid transition.

### Recovery actions
1. `transition_call(db, call_id, COMPLETED)` raises `InvalidTransition`.
2. `EventProcessor` catches it, returns `processed=False`.
3. DB state remains `RINGING` — no corruption.

### What happens to the later `ANSWERED` event
If `ANSWERED` subsequently arrives (correct order restored), it is processed normally:
- `RINGING → ANSWERED` is a valid transition.
- The earlier rejected `COMPLETED` is not in `dialer_events` (it failed the state machine check before insertion).
- `COMPLETED` can be re-delivered with the correct `event_seq` after `ANSWERED`.

### Verification
Test: `TestEventProcessor::test_out_of_order_completed_before_answered`

---

## 5. Agent Availability Drop

### Scenario
Several agents log out or disconnect mid-session, reducing `AVAILABLE` count from 20 to 2.

### Detection mechanism
`SafetyController.evaluate()` reads the **live** `DialerAgent` table at decision time. It never caches agent counts.

### Recovery actions
1. Pacing engine continues to recommend based on rolling history (may still suggest 10 dials).
2. Safety Controller reads DB: `available_agents = 2`.
3. In PREDICTIVE mode: `approved_dials = min(proposed, max_overhang - in_flight, available) = min(10, 5-3, 2) = 2`.
4. In PROGRESSIVE mode: `approved_dials = available = 2`.
5. If `available_agents = 0`: `approved_dials = 0` (REJECTED verdict).

### Progressive fallback is automatic
No manual intervention is required. The safety controller degrades gracefully with real-time DB reads.

---

## 6. Database Unavailability

### Scenario
The database file is locked (SQLite) or the connection pool is exhausted (PostgreSQL).

### Current behaviour
- `SafetyController` wraps `evaluate()` in `try/except Exception`. Any DB error → `REJECTED` verdict with `approved_dials=0`.
- **Fail closed**: The dialer stops placing calls rather than continuing unsafely.

### Verification
Test: `TestSafetyController::test_fail_closed_on_exception` — passes a non-Session object to `evaluate()`, asserts `verdict=REJECTED`, `approved_dials=0`.

---

## 7. Borrower Double-Dial Prevention

### Scenario
Two dialing workers simultaneously select the same borrower for dialing.

### Detection mechanism
`dialer_borrower_locks` table has:
```sql
UNIQUE (borrower_id)
```

### Recovery actions
1. First worker: `INSERT INTO dialer_borrower_locks (borrower_id, ...)` succeeds.
2. Second worker: `INSERT` raises `IntegrityError` (UNIQUE violation).
3. Second worker selects the next available unlocked borrower.

### Lock TTL
Each lock has an `expires_at` timestamp. `recover_stale_state()` removes expired locks so borrowers are not permanently locked if a worker crashes holding a lock.

---

## Summary Table

| Failure | Detection | Recovery | Verified |
|---|---|---|---|
| Worker crash | Startup TTL scan | Stale calls → FAILED, agents released | ✅ Test |
| Provider outage | Consecutive failure counter | Circuit OPEN → fallback to progressive | ✅ Test |
| Duplicate event | DB UNIQUE(call_id, type, seq) | Second insert rejected, state unchanged | ✅ Test |
| Out-of-order event | State machine transition guard | Invalid transition rejected, state unchanged | ✅ Test |
| Agent dropout | Live DB read in Safety Controller | Approved dials capped at available count | ✅ Test |
| DB error | try/except in SafetyController | REJECTED / fail closed | ✅ Test |
| Double borrower dial | DB UNIQUE(borrower_id) | Second lock insert rejected | ✅ Model |
