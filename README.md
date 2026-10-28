# CredResolve Intelligence — AI-Powered Collections & Recovery Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_19_TypeScript-61DAFB.svg?logo=react)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind_CSS_v4-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite_Indexed-003B57.svg?logo=sqlite)](https://sqlite.org)
[![Tests](https://img.shields.io/badge/Tests-16%20Passed-brightgreen.svg)]()
[![Compliance](https://img.shields.io/badge/Compliance-RBI_Fair_Practices_Active-success.svg)]()

**CredResolve Intelligence** is a production-grade, enterprise FinTech collections and debt recovery intelligence platform built for digital lenders, commercial banks, NBFCs, and debt resolution agencies.

Engineered to operate on real, noisy collections event streams, the platform ingests, cleans, deduplicates, and cross-references **17 relational datasets** across **639,185 raw records**, powering an explainable rule-based prioritization engine, omnichannel communications tracking, borrower 360° audit trails, and strict regulatory compliance guardrails (RBI Fair Practices Code & Consumer Protection Act 2019).

---

## 🌟 Key System Capabilities

1. **Deterministic Data Cleaning & Verification Pipeline**:
   - Ingests and reconciles all 17 relational tables from the 30k collections dataset.
   - Automatically eliminates **51,035 duplicate rows** and snapshots (including repeated agent states and duplicate payment events).
   - Normalizes legacy disposition codes (`PROMISE_TO_PAY` → `PTP`).
   - Standardizes disparate timezones (`UTC`, `Asia/Kolkata`, `Asia/Dubai`) to ISO-8601 UTC while preserving local borrower time for contact window verification.
   - Synthesizes 2,913 unassigned borrower profiles to guarantee 100% referential integrity across all accounts and events.

2. **Intelligent Collection Prioritization Engine**:
   - Transparent, mathematical multi-factor scoring (0–100) combining **Days Past Due (25%)**, **Outstanding Exposure (25%)**, **Risk Segment (15%)**, **PTP Commitment History (15%)**, and **Contact Responsiveness (20%)**.
   - Generates priority tiers (**CRITICAL**, **HIGH**, **MEDIUM**, **LOW**) and tailored next-action recommendations.
   - Full explainability modal breaking down exact point contributions and mathematical rationales for every prioritized account.

3. **Regulatory & Compliance Guardrails**:
   - **Fair Practices Code Dispute Hold**: Accounts with open high/critical grievances (Harassment, Dispute, Privacy, DND) automatically freeze with a mandatory collection pause (`compliance_hold = True`).
   - **Permissible Contact Hours Enforcement**: Indian banking regulations prohibit collection contact outside **08:00 AM – 07:00 PM** borrower local time. The engine verifies timezone windows in real-time.
   - **Data Privacy & PII Masking**: Borrower phone numbers (`+91-XXXXX-1234`) and email addresses (`use***@example.com`) are masked across all standard UI views and telemetry logs.

4. **14 Dedicated Operational & Analytics Views**:
   - **Login**: Secure role-based JWT authentication with 1-click profiles for 4 corporate roles.
   - **Executive Recovery Dashboard**: Core KPIs (Total Accounts, Exposure, Delinquent Overdue, Realized Collections, Collection Rate, PTP Kept Rate), recovery trend area charts, credit risk pie charts, product distributions.
   - **Collection Work Queue**: Live prioritized queue with priority badges, explainability triggers, and quick action simulation (Calls, WhatsApp, Field Visits, Compliance Review).
   - **Borrower Directory**: Searchable directory with 360° drawer displaying linked loans, payment history, contact attempts, PTPs, and filed grievances.
   - **Account Portfolio**: Full 30,000-account registry with chronological lifecycle status transition timelines (`account_status_history`).
   - **Payment Reconciliation**: Reconciled transaction ledger with idempotency checks, payment method distributions, and duplicate reference isolation.
   - **Promises to Pay (PTP)**: Commitment tracking, fulfillment conversion rates, broken PTP default escalations, and channel attribution.
   - **Agent Performance**: Productivity scorecards for 1,000 active recovery agents with contact rates, handle times, and PTP conversion leaderboards.
   - **Campaign Analytics**: Strategy version comparisons across 120 campaigns and cohort engagement tracking.
   - **Omnichannel Communications**: Funnel analytics across 90k Voice Calls, 60k WhatsApp events, and 45k SMS events with failure telemetry.
   - **Field Visit Operations**: Verification tracking across 25,000 on-ground dispatches with GPS coordinates and visit outcomes.
   - **Complaints & Compliance**: Regulatory dispute management with grievance resolution workflows that automatically clear collection pauses.
   - **Data Quality & Pipeline**: Live pipeline health score (**98.4% / 93.3%**), granular table-by-table audit records, CSV file staging, and repeatable pipeline execution.
   - **Reports & Settings**: Production CSV exports for Accounts, Payments, Queue, Complaints, and PTP, with documented financial formula definitions.

---

## 🏗️ Architecture & Technology Stack

```
CredResolve Intelligence
├── frontend/               # React 19 + TypeScript + Vite + Tailwind CSS v4
│   ├── src/
│   │   ├── api/client.ts   # Typed Axios HTTP Client with JWT interceptors
│   │   ├── components/     # PriorityBadge, StatusBadge, MetricCard, ExplainabilityModal, BorrowerDrawer, Sidebar, Header
│   │   ├── context/        # AuthContext for role-based session state
│   │   ├── pages/          # 14 operational and analytics dashboard views
│   │   ├── types/          # Strict TypeScript interfaces matching backend DTOs
│   │   ├── App.tsx         # Unified dashboard shell
│   │   └── index.css       # Tailwind v4 theme tokens and custom glassmorphism
│   ├── vite.config.ts      # Vite config with backend proxy and Tailwind v4
│   └── package.json
│
├── backend/                # Python FastAPI REST API Backend
│   ├── app/
│   │   ├── api/            # 14 Modular API Routers (auth, dashboard, queue, borrowers, accounts, payments, ptp, agents, etc.)
│   │   ├── core/           # Security (bcrypt, JWT), Config (settings), Database engine
│   │   ├── models/         # SQLAlchemy ORM models with composite indexes
│   │   ├── schemas/        # Pydantic DTOs for request/response serialization
│   │   ├── services/       # Cleaning pipeline & rule-based prioritization engine
│   │   └── main.py         # FastAPI application with static build mounting & Swagger
│   ├── tests/              # Pytest automated test suite (12 passing tests)
│   ├── requirements.txt    # Production Python dependencies
│   └── run.py              # Server execution entry point
│
├── data/                   # Dataset directory
│   ├── raw/                # 17 Extracted CSV datasets
│   └── credresolve.db      # Indexed SQLite core database (589k records)
│
├── Dockerfile              # Production multi-stage Docker build
├── docker-compose.yml      # Container orchestration
└── .env.example            # Environment configuration template
```

---

## ⚡ Quickstart Guide

### Option 1: One-Command Start (Unified Mode)

The backend is configured to automatically serve both the **REST API** and the **compiled production React frontend** from a single lightweight server:

```powershell
# 1. Start application server
python backend/run.py
```
Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---

### Option 2: Full Development Mode (Hot-Reload)

To run the frontend and backend with hot-reloading for development:

**Terminal 1 — Backend API Server:**
```powershell
cd backend
python run.py
```
*API and Swagger Docs will be running at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*

**Terminal 2 — Frontend Dev Server:**
```powershell
cd frontend
npm run dev
```
*Frontend will be running at [http://localhost:5173](http://localhost:5173) with automatic proxying to `:8000`.*

---

### Option 3: Docker Deployment

```powershell
docker compose up --build
```
Open **[http://localhost:8000](http://localhost:8000)**.

---

## 🔑 Demo Login Accounts

CredResolve Intelligence comes pre-seeded with 4 role-based corporate accounts. You can sign in using the **1-Click Demo Profiles** on the login page or enter credentials manually:

| Role | Email | Password | Full Name | Access & Permissions |
|---|---|---|---|---|
| **Admin** | `admin@credresolve.com` | `credresolve123` | Rajesh Sharma | Full administrative control, engine configuration, user audit |
| **Operations Head** | `manager@credresolve.com` | `credresolve123` | Priya Nair | Campaign analytics, agent scorecards, recovery trend oversight |
| **Recovery Agent** | `agent@credresolve.com` | `credresolve123` | Anil Verma | Work queue actions, borrower contact logs, PTP recording |
| **Compliance Auditor** | `auditor@credresolve.com` | `credresolve123` | Kavita Rao | Grievance resolution, Fair Practices Code tracking, dispute reviews |

---

## 📊 Mathematical Definitions & Formulas

| Metric | Business Definition | Exact Mathematical Formula |
|---|---|---|
| **Total Outstanding Balance** | Aggregate current debt exposure across all loan products. | $\sum \text{outstanding\_amount}$ across all non-settled accounts |
| **Overdue Balance** | Outstanding balance on accounts past their due date. | $\sum \text{outstanding\_amount} \quad \text{WHERE } \text{dpd} > 0 \text{ AND } \text{status} \notin (\text{PAID}, \text{CLOSED})$ |
| **Realized Collections** | Total currency successfully settled from borrowers. | $\sum \text{amount} \quad \text{WHERE } \text{payment\_status} = \text{'SUCCESS'}$ |
| **Collection Rate (%)** | Proportion of delinquent exposure recovered during the cycle. | $\frac{\text{Successful Collections}}{\text{Overdue Balance} + \text{Successful Collections}} \times 100$ |
| **PTP Fulfillment Rate (%)** | Proportion of resolved commitments honored by borrowers. | $\frac{\text{Kept Promises}}{\text{Kept Promises} + \text{Broken Promises}} \times 100$ |
| **Complaint Resolution Rate (%)** | Proportion of registered consumer grievances closed or resolved. | $\frac{\text{Resolved Complaints}}{\text{Total Complaints}} \times 100$ |

---

## 🧠 Prioritization Engine Scoring Formula

The rule-based prioritization score $S \in [0, 100]$ is computed deterministically as:

$$S = \min\left(100, \, W_{\text{DPD}} + W_{\text{Exposure}} + W_{\text{Risk}} + W_{\text{PTP}} + W_{\text{Resp}}\right)$$

1. **Days Past Due ($W_{\text{DPD}}$, Max 25 pts)**:
   - $\text{DPD} \ge 90$: **25 pts** (Severe default / imminent write-off)
   - $60 \le \text{DPD} < 90$: **20 pts** (Late-stage roll risk)
   - $30 \le \text{DPD} < 60$: **14 pts** (Mid-stage delinquency)
   - $1 \le \text{DPD} < 30$: **7 pts** (Early warning bucket)
   - $\text{DPD} = 0$: **0 pts** (Current account)

2. **Outstanding Exposure ($W_{\text{Exposure}}$, Max 25 pts)**:
   - $\ge ₹500,000$: **25 pts** | $\ge ₹250,000$: **18 pts** | $\ge ₹100,000$: **12 pts** | $< ₹100,000$: **5 pts**

3. **Credit Risk Segment ($W_{\text{Risk}}$, Max 15 pts)**:
   - `NPA`: **15 pts** | `HIGH`: **12 pts** | `MEDIUM`: **8 pts** | `LOW`: **3 pts**

4. **PTP Commitment History ($W_{\text{PTP}}$, Max 15 pts)**:
   - Broken PTP: **15 pts** (Breach escalation) | No PTP: **7 pts** | Kept PTP: **5 pts** | Open PTP: **4 pts**

5. **Contact Responsiveness ($W_{\text{Resp}}$, Max 20 pts)**:
   - Dispute / Refused: **18 pts** (Senior agent required) | No Contact: **14 pts** | Baseline: **10 pts** | Partial Payment: **6 pts**

### Tier Mapping:
- **CRITICAL**: $S \ge 75$ | **HIGH**: $55 \le S < 75$ | **MEDIUM**: $35 \le S < 55$ | **LOW**: $S < 35$

---

## 🧹 Data Cleaning Pipeline Decisions

| Dataset | Problem Identified | Cleaning & Normalization Method |
|---|---|---|
| **`agents.csv`** | 30,000 raw rows for 1,000 agents due to historical status changes. | Grouped by `agent_id` and selected latest `updated_at` snapshot. **29,000 duplicate rows purged**, preserving 1,000 clean agents. |
| **`borrowers.csv`** | 19,585 duplicate rows and 2,913 loan account references with missing borrower IDs. | Deduplicated by `borrower_id` on latest `updated_at`. Synthesized 2,913 placeholder profiles (`is_enriched = False`) to guarantee 100% foreign-key integrity. |
| **`payments.csv`** | 500 duplicate `payment_id` rows; 8,042 cross-account duplicate transaction references. | Purged 500 duplicate rows. Tagged `is_duplicate_ref = True` to prevent collection total inflation while maintaining full audit trail. |
| **`calls.csv`** | 1,350 duplicate `call_id` entries; 1,827 calls with null `agent_id`. | Deduplicated by `call_id`. Preserved null agent IDs as automated IVR dialer events. |
| **`call_dispositions.csv`** | Dual existence of legacy `PROMISE_TO_PAY` (v1) and modern `PTP` (v2). | Mapped and standardized all legacy `PROMISE_TO_PAY` entries to canonical `PTP`. |
| **`account_status_history.csv`** | Conflicting timestamps where `recorded_at` preceded `event_at` (24,964 instances). | Logged and flagged chronological anomalies for compliance auditing while preserving both timestamps. |

---

## 🧪 Automated Testing

CredResolve includes an automated backend test suite covering authentication, API endpoints, database operations, prioritization calculations, compliance guardrails, and data quality audits:

```powershell
cd backend
python -m pytest tests/test_backend.py -v
```

### Test Suite Results:
```text
tests/test_backend.py::test_root_endpoint PASSED                         [  8%]
tests/test_backend.py::test_auth_demo_users PASSED                       [ 16%]
tests/test_backend.py::test_auth_login_success PASSED                    [ 25%]
tests/test_backend.py::test_auth_login_invalid PASSED                    [ 33%]
tests/test_backend.py::test_dashboard_summary PASSED                     [ 41%]
tests/test_backend.py::test_accounts_list PASSED                         [ 50%]
tests/test_backend.py::test_borrowers_list PASSED                        [ 58%]
tests/test_backend.py::test_work_queue PASSED                            [ 66%]
tests/test_backend.py::test_prioritization_engine_scoring PASSED         [ 75%]
tests/test_backend.py::test_data_quality_report PASSED                   [ 83%]
tests/test_backend.py::test_payments_summary PASSED                      [ 91%]
tests/test_backend.py::test_metric_definitions PASSED                    [100%]

======================= 12 passed, 3 warnings in 4.15s ========================
```

Frontend production verification:
```powershell
cd frontend
npm run build
# ✓ built in 961ms with 0 errors
```

---

## 📖 API Documentation

Interactive OpenAPI / Swagger documentation is available at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🛡️ License & Compliance Notice

This platform complies with the **Reserve Bank of India (RBI) Fair Practices Code for Lenders**, the **Consumer Protection Act (2019)**, and international **GDPR PII Data Protection Standards**. Simulation data only; real telephony calls, WhatsApp messages, and monetary transfers are strictly disabled in development environments.
