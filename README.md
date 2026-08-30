# Razorpay AI Revenue Recovery

Razorpay AI Revenue Recovery is a test-mode-only system that turns failed payments into safe, auditable recovery cases. It diagnoses the failure, scores recovery likelihood from customer context, selects a deterministic action, applies policy safeguards, and measures the outcome in PostgreSQL. See [the five-minute demo script](DEMO_SCRIPT.md) and [architecture guide](ARCHITECTURE_DIAGRAM.md).

## Quick start

```bash
docker compose up -d db
cd backend && .venv/bin/python -m uvicorn app.main:app --reload --host localhost --port 8000
cd frontend && npm run dev -- --hostname localhost --port 3000
```

Open `http://localhost:3000/dashboard`. The API health check is `http://localhost:8000/health`. Use only Razorpay test-mode credentials in `.env`.

## What it does

- Detects eligible failed Razorpay test-mode payments.
- Maps gateway errors to root-cause diagnoses.
- Calculates deterministic recovery probability and revenue at risk.
- Uses customer history, LTV, activity, and churn signals to recommend recovery actions.
- Enforces policy limits before any action executes.
- Tracks outcomes and measures recovered revenue.
- Records every step in an auditable PostgreSQL timeline.

## Technology

- Backend: Python, FastAPI, SQLAlchemy, PostgreSQL, optional Claude reasoning.
- Frontend: Next.js, React, TypeScript, Tailwind CSS, Recharts.
- Payments: Razorpay Test Mode APIs only.

## Key features

- Root-cause diagnosis instead of indiscriminate retries.
- Context-aware action selection and rejected-alternative reasoning.
- Deterministic policy enforcement; Claude is explanation-only with a validated fallback.
- Complete audit trail and batch-level recovery metrics.

## Demo

From the dashboard, select **Process 12 test-mode payments**, wait for the batch status to complete, then select a case to inspect its decision and audit timeline. If the Razorpay test account contains no eligible failed payments, the dashboard honestly presents its empty state. Full presenter guidance is in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).
