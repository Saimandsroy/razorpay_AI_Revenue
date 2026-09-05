# Razorpay AI Revenue Recovery

### Payments fail. Revenue shouldn’t.

**An AI-enriched, policy-controlled recovery operating system for failed Razorpay Test Mode payments.** It turns a failed payment into an auditable recovery case: diagnose the root cause, understand the customer context, select a deterministic action, enforce safety guardrails, and measure the outcome.

[![Status: Buildathon](https://img.shields.io/badge/status-Buildathon-2563eb?style=flat-square)](#demo-in-under-two-minutes)
[![Razorpay: Test Mode](https://img.shields.io/badge/Razorpay-Test%20Mode-0f766e?style=flat-square)](#safety-by-design)
[![Backend: FastAPI](https://img.shields.io/badge/backend-FastAPI-059669?style=flat-square)](#technology)
[![Frontend: Next.js 14](https://img.shields.io/badge/frontend-Next.js%2014-111827?style=flat-square)](#technology)
[![Database: PostgreSQL](https://img.shields.io/badge/database-PostgreSQL-336791?style=flat-square)](#technology)
[![AI: Gemini](https://img.shields.io/badge/AI-Gemini%20%28bounded%29-7c3aed?style=flat-square)](#ai-can-reason-policy-remains-in-control)

[Demo](#demo-in-under-two-minutes) · [Architecture](#system-architecture) · [Quick start](#run-it-locally) · [API surface](#api-surface)

> **Revenue Recovery Command Center** — visibility into failed payments, recovery opportunities, actions, customer responses, and recovered revenue.

<!-- Screenshot slot: capture the dashboard at /dashboard and add it as docs/images/dashboard.png. -->

---

## The problem: a failed payment is not always a lost customer

An expired card, temporary cash-flow issue, rejected mandate, or incomplete authentication can look identical in a basic payment report: **failed**. But the right next step is very different for each customer.

| Traditional handling | Recovery intelligence |
| --- | --- |
| `FAILED → FAILED` | `FAILED → UNDERSTAND → ACT → RECOVER → MEASURE` |
| One-size-fits-all retries | Root-cause diagnosis and context-aware action selection |
| No explanation of why an action happened | A decision and its rejected alternatives are auditable |
| Revenue loss is assumed | Payment capture and recovered revenue are measured |

This project answers six operational questions for every eligible failed payment:

1. **Why** did it fail?
2. **Can** it realistically be recovered?
3. **Which** recovery action fits this customer and failure?
4. **Is** that action allowed by policy?
5. **What** happened after the action?
6. **How much** revenue was actually recovered?

---

## A revenue recovery operating system

| 01 — Detect | 02 — Understand | 03 — Recover | 04 — Measure |
| --- | --- | --- | --- |
| Ingest eligible failed Razorpay Test Mode payments and create recovery cases. | Normalize gateway errors, diagnose root cause, retrieve payment history, and calculate score, risk, and priority. | Apply deterministic policy, record the permitted recovery action, and track customer interaction. | Track payment outcome, attribute revenue only after capture, and expose batch metrics plus case-level audit evidence. |

Not every case should be acted on. A churned customer, repeated mandate rejection, disputed payment, retry-limit breach, or gateway anomaly can stop an action before execution.

---

## What makes this different?

| Differentiator | What it means in practice |
| --- | --- |
| **Detection is only the beginning** | The system maps Razorpay error codes to root causes such as `card_expired`, `insufficient_funds`, `mandate_rejected`, and authentication failure. |
| **Context-aware, deterministic actions** | Customer payment history, lifetime value, inactivity, failure history, and recovery score influence the recommended action. |
| **Policy-first recovery** | Deterministic guardrails stop unsafe retries and disallowed outreach before the executor runs. |
| **Alternative-action reasoning** | Each decision persists the recommended action and explains why competing actions were rejected. |
| **Outcome tracking** | Recovery actions progress through delivery and customer-response states; revenue is attributed only after a captured payment. |
| **End-to-end auditability** | PostgreSQL records cases, actions, outcomes, and chronological audit events for review. |

## AI can reason. Policy remains in control.

Gemini is a **bounded explanation layer**, not a financial decision-maker.

- The deterministic recovery engine computes diagnosis, score, recommendation, and policy decision **before** Gemini runs.
- Gemini receives that already-computed context and can return only structured reasoning, confidence, and rejected-alternative explanations.
- Gemini output cannot select, alter, or override a recovery action or policy result.
- Missing configuration, invalid JSON, timeouts, rate limits, and provider errors fall back safely to deterministic reasoning and are logged as `GEMINI_REASONING_RECEIVED` audit metadata.

> **Control boundary:** Gemini enriches an explanation; deterministic recovery logic and policy remain authoritative.

---

## Recovery decision pipeline

```text
Failed payment
      ↓
Detection + failure normalization
      ↓
Root-cause diagnosis
      ↓
Customer history + LTV + activity signals
      ↓
Deterministic recovery score + revenue at risk + priority
      ↓
Gemini reasoning (optional explanation only)
      ↓
Deterministic policy gate
   ↙                         ↘
STOP + audit event            ALLOW
                                  ↓
                         Recovery action
                                  ↓
                         Customer response
                                  ↓
                          Payment capture
                                  ↓
                          Revenue recovered
                                  ↓
                     PostgreSQL audit + metrics
```

## System architecture

```mermaid
flowchart LR
    RP[Razorpay Test Mode<br/>failed payment] --> API[FastAPI API]
    API --> D[Detection & normalization]
    D --> X[Diagnosis]
    X --> C[Customer context<br/>history · LTV · activity]
    C --> S[Deterministic scoring<br/>risk · priority]
    S --> A[Context-aware<br/>deterministic action]
    A --> P{Deterministic<br/>policy gate}

    C -. explanation context .-> G[Gemini<br/>structured reasoning only]
    G -. audit enrichment<br/>never action authority .-> AU[Audit events]

    P -->|Stopped| AU
    P -->|Allowed| E[Bounded executor<br/>links · plans · proposals]
    E --> R[Recovery actions<br/>customer events]
    R --> O[Outcome tracker<br/>capture attribution]

    D --> DB[(PostgreSQL)]
    AU --> DB
    E --> DB
    O --> DB
    DB --> UI[Next.js Command Center<br/>metrics · cases · audit timeline]
```

---

## Safety by design

| Guardrail | Enforced behavior |
| --- | --- |
| **Razorpay Test Mode only** | Configuration rejects non-`rzp_test_` key IDs. |
| **No blind expired-card retry** | The policy gate blocks a retry against an expired card. |
| **Mandate protection** | Rejected mandates cannot be retried; repeated rejections are stopped. |
| **Customer protection** | Disputes, churn over 60 days, and retry-limit breaches stop recovery. |
| **Gateway intelligence** | Anomaly-aware retry suppression is supported by the deterministic policy layer. |
| **No silent execution failure** | Executor errors are persisted as a failed execution instead of crashing a batch. |
| **Honest outcomes** | Pending remains pending at timeout; recovered revenue is not credited before capture. |
| **Idempotent case ingestion** | A repeated payment ID returns the existing recovery case instead of creating another one. |

The executor is deliberately bounded: a retry is recorded rather than re-charging an existing failed payment; downgrade offers require merchant/customer confirmation; payment links are created in Razorpay Test Mode.

---

## Command Center

The Next.js dashboard is backed by FastAPI and PostgreSQL—not hard-coded metrics.

| View | What a reviewer can inspect |
| --- | --- |
| **Dashboard** | Cases analyzed, revenue at risk, recovered revenue, recovery rate, diagnosis/action breakdowns, and sortable cases. |
| **Case detail** | Customer/payment context, diagnosis, score, recommendation, policy rationale, execution status, outcome, and full audit trail. |
| **Recovery actions** | Action status, channel, provider reference, customer interaction, and recovery attribution. |
| **Audit feed** | Cross-case chronological operational evidence. |
| **Safe simulator** | A deterministic demonstration flow for detection, actions, customer response, and recovered revenue—without calling Razorpay. |

---

## Demo in under two minutes

1. Start PostgreSQL, backend, and frontend using the commands below.
2. Open [`http://localhost:3000/dashboard`](http://localhost:3000/dashboard).
3. Select **Run Safe Demo**. This creates a local PostgreSQL-backed synthetic batch and does **not** call Razorpay.
4. Review KPI cards, diagnosis/action charts, and the recovery-case table.
5. Open a case to inspect its policy decision, recovery action, outcome, and audit timeline.
6. Use the simulator controls to advance responses and recoveries when demonstrating the full lifecycle.

For the live Razorpay path, use **Process 12 Payments** with eligible failed payments in a Razorpay **test** account. If none are available, the dashboard correctly shows no recoverable cases; it never fabricates production data.

Detailed presenter notes: [DEMO_SCRIPT.md](DEMO_SCRIPT.md) · [Architecture walkthrough](ARCHITECTURE_DIAGRAM.md) · [Judge quick start](QUICK_START_JUDGES.md)

---

## Run it locally

### Prerequisites

- Docker Desktop
- Python 3.11+
- Node.js 18+
- Razorpay **test-mode** credentials for live ingestion (optional for safe simulator)
- Gemini API key (optional; deterministic fallback works without it)

### 1. Configure environment

```bash
cd razorpay-recovery
cp .env.example .env
```

Set only test-mode values in `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://recovery:recovery@localhost:5433/recovery
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_test_secret
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_SECONDS=2.5
```

> Never commit `.env`, Razorpay secrets, or Gemini keys. The safe simulator works without either external provider.

### 2. Start PostgreSQL

```bash
docker compose up -d db
docker compose exec db pg_isready -U recovery -d recovery
```

PostgreSQL is published on host port `5433`. The Compose initialization script creates `recovery_batches`, `recovery_cases`, `recovery_actions`, and `audit_events` on a fresh database volume.

### 3. Start the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --host localhost --port 8000
```

Verify it:

```bash
curl http://localhost:8000/health
```

### 4. Start the dashboard

```bash
cd frontend
npm install
npm run dev -- --hostname localhost --port 3000
```

Open [`http://localhost:3000/dashboard`](http://localhost:3000/dashboard). Use `localhost`, not `127.0.0.1`, so the configured CORS origin matches.

### 5. Run checks

```bash
cd backend
.venv/bin/pytest tests/ -v

cd ../frontend
npm run build
```

The live Gemini smoke test runs only when its key and model are configured; normal tests do not require a real provider key.

---

## API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service and Razorpay Test Mode configuration status. |
| `POST /api/v1/cases/process` | Process one eligible failed payment through the pipeline. |
| `POST /api/v1/batch/process?batch_size=12` | Start a bounded Razorpay Test Mode batch. |
| `POST /api/v1/demo/batch` | Create a safe local demo batch; unavailable in production mode. |
| `POST /api/v1/demo/recovery-batch` | Create a staged simulator batch. |
| `POST /api/v1/demo/batch/{id}/advance` | Process simulator cases through detection and action creation. |
| `POST /api/v1/demo/batch/{id}/simulate-responses` | Simulate customer interaction events. |
| `POST /api/v1/demo/batch/{id}/simulate-recoveries` | Simulate successful recovery captures. |
| `GET /api/v1/batch/{id}/summary` | Batch KPIs and diagnosis/action breakdowns. |
| `GET /api/v1/batch/{id}/cases` | Recovery cases for a batch. |
| `GET /api/v1/cases/{id}/journey` | Customer recovery journey, actions, timeline, and revenue. |
| `GET /api/v1/cases/{id}/audit` | Chronological audit evidence for one case. |
| `GET /api/v1/recovery-actions` | Filterable recovery-action records. |
| `POST /api/v1/recovery-actions/{id}/events` | Validate and record a customer interaction event. |

Interactive API documentation is available at [`http://localhost:8000/docs`](http://localhost:8000/docs) when the backend is running.

---

## Technology

| Layer | Implementation |
| --- | --- |
| Backend | Python · FastAPI · SQLAlchemy · Pydantic Settings |
| Intelligence | Deterministic diagnosis, scoring, context-aware actions, policy gate, gateway-anomaly signals |
| AI enrichment | Google Gemini via the official `google-genai` SDK with structured JSON validation and fallback |
| Payments | Razorpay SDK in Test Mode |
| Persistence | PostgreSQL 16 · JSONB audit metadata |
| Frontend | Next.js 14 · React · TypeScript · Tailwind CSS · Recharts · Lucide |
| Verification | Pytest · deterministic simulator · real PostgreSQL verification script |
| Local infrastructure | Docker Compose · GitHub |

---

## Repository guide

```text
backend/
  app/                 FastAPI routes, models, schemas, recovery services
  tests/               Unit, integration, simulator, action, and provider tests
  scripts/             E2E, integrity, and PostgreSQL verification scripts
frontend/
  src/app/             Command Center pages and route views
  src/app/components/  Dashboard charts, timelines, simulator, and action UI
infra/postgres/        Fresh-schema initialization and recovery-actions migration
DEMO_SCRIPT.md         Presenter flow
ARCHITECTURE_DIAGRAM.md Architecture notes
QUICK_START_JUDGES.md  Fast setup path for judges
```

---

## Built for the Razorpay Buildathon

Razorpay AI Revenue Recovery is designed around one operating principle:

> **Make recovery decisions explainable, policy-bounded, measurable, and useful to the merchant—not merely automated.**

This repository is intentionally test-mode-first. It is a buildathon demonstration of recovery intelligence and operational controls, not a claim that AI should autonomously make financial decisions.
