# CredResolve Intelligence — SmartDialer

A SmartDialer prototype for collections and recovery operations, designed to improve agent utilization while preserving deterministic call-safety controls.

![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)
![React](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB?logo=react)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python)
![Tests](https://img.shields.io/badge/SmartDialer%20Tests-63%20Passed-brightgreen)

## Table of Contents

- [Overview](#overview)
- [SmartDialer Features](#smartdialer-features)
- [Architecture](#architecture)
- [Dialing Modes](#dialing-modes)
- [Safety and Correctness](#safety-and-correctness)
- [Failure Handling](#failure-handling)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Simulation and Load Testing](#simulation-and-load-testing)
- [API Documentation](#api-documentation)
- [Limitations](#limitations)
- [Documentation](#documentation)

---

## Overview

CredResolve is an AI-powered collections and recovery platform. This repository extends the existing application with a SmartDialer functional prototype that automates outbound call allocation for collections agents.

The SmartDialer addresses a core operational challenge: improving agent utilization without allowing more agent-bound outbound calls than the safety rules permit.

The implementation includes:

- Progressive and predictive dialing logic.
- A separate Safety Controller between pacing decisions and call allocation.
- Agent and call state machines.
- Concurrency-aware agent and borrower allocation.
- Mock telecom provider integrations.
- Duplicate and out-of-order event handling.
- Crash recovery and provider circuit-breaker logic.
- Simulation scenarios, automated tests, and a basic load-testing utility.
- A React-based SmartDialer interface.

The prototype uses simulated telecom providers. It does not require a live telephony account to demonstrate the main workflows.

## SmartDialer Features

### 1. Progressive Dialing

Progressive dialing follows a conservative allocation strategy: an available agent can be assigned at most one new agent-bound outbound call at a time.

The implementation considers:

- Agent availability and reservation.
- Borrower selection and allocation.
- Call initiation and state transitions.
- Failed call handling.
- Agent availability changes during call setup.

The purpose is to maintain predictable allocation behavior and avoid overcommitting available agents.

### 2. Predictive Pacing Engine

The pacing engine estimates how aggressively a campaign can dial. It can propose additional calls based on campaign conditions and dialing metrics.

The engine is separate from the mechanism that actually authorizes calls.

A pacing proposal is not permission to initiate a call. Every proposal must pass through the Safety Controller.

### 3. Safety Controller

The Safety Controller acts as a mandatory safety boundary between pacing logic and call allocation.

It can:

- Approve a permitted number of calls.
- Reduce the proposed number of calls.
- Reject a request when safety conditions are not met.
- Fall back to progressive behavior when required.

The controller enforces the available-agent limits and prevents the predictive pacing logic from directly bypassing the safety decision.

### 4. Agent and Call State Machines

Explicit state transitions make the lifecycle of agents and calls easier to validate and recover.

**Agent lifecycle** includes states such as:

`OFFLINE → AVAILABLE → RESERVED → DIALING → CONNECTED → WRAP_UP`

Additional states support situations such as pausing an agent or making an agent unavailable.

**Call lifecycle** includes states such as:

`QUEUED → RESERVED → INITIATED → RINGING → ANSWERED → CONNECTED → COMPLETED`

Failure and cancellation paths are also supported.

The state machines validate transitions so that events cannot freely overwrite the current state.

### 5. Mock Telecom Providers

The application uses a provider abstraction so the dialer does not need to depend on a particular telecom vendor.

The mock providers can simulate different operational behavior, including:

- Successful call initiation.
- Provider failures and timeouts.
- Variable response latency.
- Duplicate events.
- Events arriving out of order.

These mocks allow failure scenarios to be exercised without placing real calls.

### 6. Event Processing and Recovery

The event-processing components address common distributed-system failure cases:

- Duplicate provider events.
- Out-of-order events.
- Repeated state-transition attempts.
- Stale reservations.
- Worker interruptions during call setup.
- Provider health changes.

The implementation includes recovery logic and circuit-breaker behavior to reduce the risk of continuing to send new calls through an unhealthy provider.

### 7. Simulation and Dashboard

The SmartDialer interface provides workflows for configuring and running dialing sessions, inspecting agent and call activity, and exploring simulation results.

The simulator supports scenarios with different answer rates, talk times, and provider conditions.

The interface is intended for demonstration and evaluation of the prototype rather than as a production telephony console.

---

## Architecture

The main call flow is:

```text
Campaign
   |
   v
Pacing Engine
(Progressive / Predictive)
   |
   v
Safety Controller
(Approve / Reduce / Reject / Fallback)
   |
   v
Call Allocator
(Agent and Borrower Reservation)
   |
   v
Mock Telecom Provider
   |
   v
Event Processor
(State Updates / Deduplication / Recovery)
```

### Component Responsibilities

| Component | Responsibility |
|---|---|
| Campaign/session management | Manages dialing sessions and campaign configuration |
| Progressive Dialer | Proposes calls based on available agents |
| Pacing Engine | Calculates proposed dialing volume |
| Safety Controller | Enforces safety limits before call allocation |
| Call Allocator | Coordinates agent and borrower reservations and call initiation |
| State Machines | Validate agent and call lifecycle transitions |
| Telecom Providers | Abstract provider behavior and simulate call outcomes |
| Event Processor | Handles provider events, duplicate delivery, and recovery |
| Simulation | Runs scenarios to examine pacing and dialing behavior |
| React Frontend | Provides the SmartDialer user interface |

### Architectural Decision

The prototype uses a modular application structure instead of introducing unnecessary microservices or distributed infrastructure.

This keeps the implementation straightforward to run locally while separating the main responsibilities of pacing, safety, allocation, provider integration, and event processing.

See [`docs/architecture_adr.md`](docs/architecture_adr.md) for the architecture decision record and [`docs/architecture_diagrams.md`](docs/architecture_diagrams.md) for additional diagrams.

---

## Dialing Modes

### Progressive Mode

Progressive mode prioritizes predictable allocation.

For example, if 10 agents are available, the system must not assign more than 10 simultaneous agent-bound outbound calls under the applicable allocation constraints.

### Predictive Mode

Predictive mode can propose additional calls based on its pacing calculation.

The Safety Controller independently evaluates that proposal against current availability and other safety constraints. If the proposed volume exceeds what is permitted, it must be reduced, rejected, or handled using the configured fallback behavior.

Predictive pacing must not directly invoke the telecom provider.

### Why Keep Them Separate?

The separation allows the pacing strategy to evolve without giving it authority to bypass the safety boundary.

This design aims to obtain some utilization benefits of predictive dialing while preserving the deterministic safety characteristics of progressive allocation.

---

## Safety and Correctness

The SmartDialer implementation addresses several important correctness requirements:

- **Agent reservation:** Prevents competing allocation attempts from freely reserving the same available agent.
- **Borrower allocation:** Uses allocation controls to reduce duplicate concurrent processing.
- **Safety enforcement:** Routes pacing proposals through the Safety Controller.
- **State validation:** Restricts agent and call lifecycle transitions.
- **Event deduplication:** Prevents repeated provider events from causing duplicate processing where supported by the event-processing logic.
- **Terminal-state protection:** Avoids replacing terminal call states with inappropriate later events.
- **Recovery:** Identifies stale reservations and supports recovery behavior.
- **Provider resilience:** Includes circuit-breaker behavior for provider failures.

These controls are implemented and covered to varying extents by the automated tests. The test results demonstrate the tested cases; they should not be interpreted as proof of production-scale distributed correctness.

---

## Failure Handling

The prototype includes logic and tests for representative failure scenarios.

| Scenario | Intended behavior |
|---|---|
| Worker interruption | Recover stale reservations according to recovery rules |
| Provider timeout | Record failure and apply provider health and retry behavior |
| Duplicate event | Avoid repeating an already-processed state transition |
| Out-of-order event | Preserve a sensible state rather than blindly applying every event |
| Agent becomes unavailable | Re-evaluate whether additional calls can safely be allocated |
| Provider health degradation | Use circuit-breaker behavior and configured fallback logic |

For implementation details, see [`docs/failure_recovery.md`](docs/failure_recovery.md).

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Data models | SQLAlchemy and Pydantic |
| Database | SQLite for local development |
| Frontend | React, TypeScript, Vite |
| Styling | Tailwind CSS |
| Testing | pytest |
| API specification | FastAPI-generated OpenAPI |
| Provider integration | Mock telecom provider adapters |
| Container support | Docker and Docker Compose configuration |

---

## Project Structure

```text
CredResolve/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── dialer.py
│   │   ├── models/
│   │   │   └── dialer_schema.py
│   │   ├── services/
│   │   │   ├── call_allocator.py
│   │   │   ├── event_processor.py
│   │   │   ├── pacing_engine.py
│   │   │   ├── progressive_dialer.py
│   │   │   ├── providers.py
│   │   │   ├── safety_controller.py
│   │   │   ├── simulation.py
│   │   │   └── state_machines.py
│   │   └── main.py
│   ├── tests/
│   │   └── test_dialer.py
│   ├── load_test.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── components/
│   │   ├── pages/
│   │   │   └── SmartDialer.tsx
│   │   └── App.tsx
│   └── package.json
├── docs/
│   ├── SMARTDIALER_README.md
│   ├── architecture_adr.md
│   ├── architecture_diagrams.md
│   ├── compliance_matrix.md
│   └── failure_recovery.md
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── README.md
```

The original CredResolve application files remain part of the repository. The files above highlight the main SmartDialer components and relevant project configuration.

---

## Getting Started

### Prerequisites

Install the following:

- Python 3.12 or a compatible supported Python version.
- Node.js and npm.
- Git.

Run the commands below from the repository root.

### 1. Set Up the Backend

Open a terminal:

```powershell
cd backend
python -m venv .venv
```

Activate the virtual environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the FastAPI server:

```powershell
python -m uvicorn app.main:app --reload --log-level debug
```

The backend API will be available at:

- API base: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Keep this terminal running.

### 2. Set Up the Frontend

Open a second terminal at the repository root:

```powershell
cd frontend
npm install
npm.cmd run dev
```

Open the local URL printed by Vite, typically:

`http://localhost:5173`

Keep the frontend and backend terminals running while using the application.

> **Note:** The frontend API client and development proxy must be configured to reach the local backend. If your environment uses different ports or configuration, follow the values in the frontend and backend configuration files.

---

## Running Tests

### SmartDialer Backend Tests

The SmartDialer-specific test suite is:

```powershell
cd backend
python -m pytest tests/test_dialer.py -q
```

**Recorded verification result:** 63 tests passed.

The suite covers areas including state machines, concurrency-aware reservation, Safety Controller behavior, event processing, crash recovery, provider behavior, and API operations.

### Original Backend Test Suite

The original CredResolve backend may have its own test suite. Run it separately if its test file is present:

```powershell
cd backend
python -m pytest tests/test_backend.py -v
```

The result of this original test suite is separate from the SmartDialer test result.

### Frontend Production Build

Run:

```powershell
cd frontend
npm.cmd run build
```

**Recorded verification result:** The TypeScript and Vite production build completed successfully.

The build emitted a warning that the main JavaScript bundle exceeded 500 kB after minification. This did not prevent the build from succeeding.

### Understanding Test Warnings

The backend test run emitted deprecation warnings, including warnings concerning `datetime.utcnow()` and dependencies used by the test client. These warnings did not cause the recorded test run to fail.

---

## Simulation and Load Testing

The repository includes a simulation component and a basic load-testing utility.

### Simulation Scenarios

The simulator supports scenarios representing different answer-rate and average-talk-time conditions, including:

- Scenario A: lower answer rate.
- Scenario B: moderate answer rate.
- Scenario C: higher answer rate.
- Scenario D: changing conditions.

Provider latency and failures can also be introduced to examine the effect on pacing, call initiation, connection outcomes, and Safety Controller decisions.

Use the SmartDialer interface and the relevant backend endpoints to run the available scenarios.

### Load Testing

A basic load-testing utility is provided at:

[`backend/load_test.py`](backend/load_test.py)

The utility is intended to help explore system behavior under load. Its presence does not imply that the application has been validated at 10,000 agents or at production telecom throughput.

### Scaling Considerations

Potential bottlenecks as the number of agents increases include:

- Database contention during agent and borrower reservation.
- Concurrent state updates and transaction locking.
- Provider latency and timeouts.
- Event-processing throughput.
- Retry volume and circuit-breaker coordination.
- Large campaign queries and simulation workloads.

Further scaling work would require workload-specific load tests, database profiling, and validation of concurrency guarantees under the intended deployment architecture.

---

## API Documentation

When the backend is running, use the automatically generated API documentation:

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

The API documentation lists the routes exposed by the running application.

---

## Limitations

This repository contains a functional prototype, not a production-ready telephony platform.

- Telecom interactions use mock providers; live calls are not required for the demonstrated workflows.
- Performance and concurrency guarantees must be validated against the intended production database and deployment topology.
- Load-testing results should be interpreted according to the environment and workload actually tested.
- Automated test results describe the cases covered by the tests and do not prove that every failure mode has been eliminated.
- Production deployment would require appropriate authentication and authorization review, secrets management, observability, operational monitoring, and compliance validation.

---

## Documentation

Additional SmartDialer documentation is available in the `docs/` directory:

- [`docs/SMARTDIALER_README.md`](docs/SMARTDIALER_README.md) — detailed SmartDialer implementation and usage notes.
- [`docs/architecture_adr.md`](docs/architecture_adr.md) — architecture decision record.
- [`docs/architecture_diagrams.md`](docs/architecture_diagrams.md) — architecture and flow diagrams.
- [`docs/compliance_matrix.md`](docs/compliance_matrix.md) — requirement and compliance mapping.
- [`docs/failure_recovery.md`](docs/failure_recovery.md) — failure handling and recovery design.

---

## Project Goal

The central design goal is to obtain as much of the utilization benefit of predictive dialing as possible while retaining the deterministic safety characteristics of progressive dialing.

The pacing engine may recommend how many calls to start. The Safety Controller must independently decide how many calls are permitted. Keeping that boundary explicit is the core principle of this SmartDialer prototype.
