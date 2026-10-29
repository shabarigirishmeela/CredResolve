# SmartDialer — Architecture Diagrams

## 1. System Architecture

```mermaid
flowchart TD
    subgraph Session["Dialing Session (DialerSession)"]
        direction TB
        mode["Mode: PROGRESSIVE | PREDICTIVE"]
    end

    subgraph Core["SmartDialer Core Loop (progressive_dialer.py)"]
        direction TB
        loop["Background Thread\nper session"]
    end

    subgraph PE["Pacing Engine (pacing_engine.py)"]
        erlang["Erlang-C / Ratio Model\nrolling answer rate, talk time"]
        pdec["PacingDecision\nproposed_dials, explanation"]
        erlang --> pdec
    end

    subgraph SC["Safety Controller (safety_controller.py)"]
        dbread["Reads DB independently\n(agent counts, circuit state)"]
        rules["Capacity rules\n+ overhang limit\n+ circuit breaker check"]
        sdec["SafetyDecision\nverdict: APPROVED | REDUCED | REJECTED | FALLBACK\napproved_dials"]
        dbread --> rules --> sdec
    end

    subgraph CA["Call Allocator (call_allocator.py)"]
        occ["OCC: UPDATE agents\nWHERE state='AVAILABLE' AND version=N"]
        lock["INSERT dialer_borrower_locks\n(unique borrower_id)"]
        cb["Circuit Breakers\nCLOSED → OPEN → HALF-OPEN → CLOSED"]
        occ --> lock --> cb
    end

    subgraph Providers["Mock Telecom Providers (providers.py)"]
        alpha["ProviderAlpha\nFast, reliable, configurable fail rate"]
        beta["ProviderBeta\nSlow, timeouts, OOO events, duplicates"]
    end

    subgraph EP["Event Processor (event_processor.py)"]
        dedup["Unique(call_id, event_type, event_seq)\n→ reject duplicate events"]
        csm["Call State Machine transition\nRINGING → ANSWERED → CONNECTED"]
        recovery["Startup recovery\nStale RESERVED → FAILED + agent release"]
        dedup --> csm --> recovery
    end

    subgraph DB["Database (SQLite / PostgreSQL)"]
        tables["dialer_sessions\ndialer_agents\ndialer_calls\ndialer_borrower_locks\ndialer_events\ndialer_provider_health\ndialer_state_logs"]
    end

    Session --> Core
    Core -->|"1. Request recommendation"| PE
    PE -->|"PacingDecision"| SC
    SC -->|"2. Read from DB"| DB
    SC -->|"SafetyDecision"| CA
    CA -->|"3. OCC reservation"| DB
    CA -->|"4. Initiate call"| Providers
    Providers -->|"5. Webhook events"| EP
    EP -->|"6. State transition"| DB
    EP -->|"7. Release agent on complete"| CA
```

---

## 2. Agent State Machine

```mermaid
stateDiagram-v2
    [*] --> OFFLINE : agent registered

    OFFLINE --> AVAILABLE : login / session join
    AVAILABLE --> RESERVED : allocator selected agent\n(OCC version check)
    RESERVED --> DIALING : call initiated with provider
    RESERVED --> AVAILABLE : allocation failed / timeout recovery
    DIALING --> CONNECTED : provider ANSWERED event received
    DIALING --> AVAILABLE : call FAILED event received
    CONNECTED --> WRAP_UP : call COMPLETED or FAILED
    WRAP_UP --> AVAILABLE : wrap-up timer expires
    AVAILABLE --> OFFLINE : agent logs out

    note right of RESERVED
        OCC prevents double-reservation.
        UPDATE WHERE state='AVAILABLE' AND version=N
        must affect exactly 1 row.
    end note

    note right of CONNECTED
        Only Safety Controller reads this state
        to compute available capacity.
        Pacing Engine never bypasses it.
    end note
```

**Valid transitions table:**

| From | To | Trigger |
|---|---|---|
| OFFLINE | AVAILABLE | Agent joins session |
| AVAILABLE | RESERVED | Allocator: OCC UPDATE succeeds |
| RESERVED | DIALING | Provider call initiated |
| RESERVED | AVAILABLE | Timeout recovery / allocation abort |
| DIALING | CONNECTED | `ANSWERED` provider event |
| DIALING | AVAILABLE | `FAILED` provider event |
| CONNECTED | WRAP_UP | `COMPLETED` or `FAILED` provider event |
| WRAP_UP | AVAILABLE | Wrap-up timer expires |
| AVAILABLE | OFFLINE | Agent exits session |

Any other transition raises `InvalidTransition`.

---

## 3. Call State Machine

```mermaid
stateDiagram-v2
    [*] --> QUEUED : call created (borrower selected)

    QUEUED --> RESERVED : agent allocated (OCC)
    RESERVED --> INITIATED : provider call initiated
    INITIATED --> RINGING : provider RINGING event
    RINGING --> ANSWERED : provider ANSWERED event
    ANSWERED --> CONNECTED : agent confirmed live
    CONNECTED --> COMPLETED : call ended normally
    CONNECTED --> FAILED : call dropped
    RINGING --> FAILED : no answer / provider error
    INITIATED --> FAILED : provider error
    RESERVED --> FAILED : timeout / crash recovery

    COMPLETED --> [*]
    FAILED --> [*]

    note right of INITIATED
        Idempotency key stored at this point.
        Duplicate RINGING / ANSWERED events
        are rejected by DB unique constraint.
    end note

    note right of FAILED
        Terminal state — no further transitions.
        Agent released to WRAP_UP.
        Borrower lock released.
    end note
```

**Idempotency rule**: `dialer_events(call_id, event_type, event_seq)` has a UNIQUE constraint. If the same event arrives twice with the same `event_seq`, the second insert fails and the event is silently discarded.

**Out-of-order rule**: The call state machine only allows valid forward transitions. A `COMPLETED` event arriving while the call is `RINGING` (skipping `ANSWERED`) raises `InvalidTransition` and is rejected without corrupting state.

---

## 4. Component Dependency Diagram

```mermaid
graph LR
    dialer_api["dialer.py\n(REST API)"]
    prog["progressive_dialer.py\n(Dialing Loop)"]
    alloc["call_allocator.py\n(OCC + Circuit Breaker)"]
    pacing["pacing_engine.py\n(Recommendation)"]
    safety["safety_controller.py\n(Firewall)"]
    ep["event_processor.py\n(Events + Recovery)"]
    prov["providers.py\n(Alpha / Beta)"]
    sm["state_machines.py\n(Transitions)"]
    schema["dialer_schema.py\n(ORM Models)"]
    db[("Database")]

    dialer_api --> prog
    dialer_api --> ep
    dialer_api --> alloc
    prog --> pacing
    prog --> safety
    prog --> alloc
    safety --> db
    alloc --> sm
    alloc --> prov
    alloc --> db
    ep --> sm
    ep --> db
    sm --> schema
    schema --> db
```

**Key isolation rule**: `pacing_engine.py` has **no import of** `safety_controller.py`. The pacing engine cannot grant its own recommendations. The Safety Controller is the only gatekeeper between the recommendation and the actual call placement.

---

## 5. Data Flow — Webhook Event

```mermaid
sequenceDiagram
    participant P as Provider (Alpha/Beta)
    participant API as POST /dialer/events
    participant EP as EventProcessor
    participant DB as Database
    participant SM as CallStateMachine

    P->>API: ANSWERED {call_id, event_seq=2}
    API->>EP: process(event)
    EP->>DB: INSERT dialer_events (call_id, ANSWERED, seq=2)
    alt Duplicate (seq=2 already exists)
        DB-->>EP: UNIQUE constraint violation
        EP-->>API: {processed: false, reason: "duplicate"}
    else First occurrence
        DB-->>EP: OK
        EP->>SM: transition_call(call_id, ANSWERED)
        SM->>DB: UPDATE dialer_calls SET state='ANSWERED' WHERE version=N
        SM->>DB: INSERT dialer_state_logs
        EP-->>API: {processed: true}
    end
```
