# Razorpay AI Revenue Recovery

A test-mode-only revenue recovery engine that diagnoses failed payments, recommends an appropriate recovery action, enforces deterministic safety policy, and makes every decision auditable.

## Project status

Phase 1 — foundation in progress. The repository contains a FastAPI service, a Next.js 14 dashboard shell, PostgreSQL schema, Docker database, and environment templates. Phase 2 will add the detection-to-audit pipeline.

## Architecture

```
frontend/     Next.js 14 + TypeScript + Tailwind dashboard
backend/      FastAPI recovery API
infra/postgres/ PostgreSQL initialization schema
```

The production workflow is: detect → diagnose → contextualize → score → decide → policy gate → execute → track → aggregate. Razorpay calls remain sandbox/test-mode only.

## Local setup

1. Copy `.env.example` to `.env` and fill in the values you have.
2. Start PostgreSQL: `docker compose up -d db`
3. Backend:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -e '.[dev]'
   uvicorn app.main:app --reload --port 8000
   ```
4. Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Open `http://localhost:3000/dashboard`; API health is at `http://localhost:8000/health`.

## Credentials

No secret is needed to run the dashboard shell or API health check. Phase 2 needs Razorpay **test-mode** `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`. Keep them only in the uncommitted `.env` file; never paste live-mode keys.

Phase 3 will optionally use `ANTHROPIC_API_KEY`, with a deterministic fallback when unavailable.

## Optional Claude reasoning

Set `ANTHROPIC_API_KEY` and `CLAUDE_MODEL` only when Phase 3 explanation enrichment is desired. Claude can add validated reasoning and confidence, but it cannot choose the recovery action, bypass the policy gate, or execute a payment action. A five-second timeout, response validation, and deterministic fallback are always applied.

## Batch execution dashboard

Start a test-mode batch with `POST /api/v1/batch/process?batch_size=50`, then poll `/api/v1/batch/{batch_id}/summary`. Cases and audit details are available at `/api/v1/batch/{batch_id}/cases`, `/api/v1/cases/{case_id}/full`, and `/api/v1/cases/{case_id}/audit`.

Before running Phase 4 locally, apply `infra/postgres/migrations/003_execution_and_metrics.sql` to the project PostgreSQL database. Executors create only Razorpay test-mode payment links; retries are recorded as scheduled and downgrade offers as proposed, never silently charged or applied.

## Deployment

`render.yaml` defines the FastAPI service; set its environment variables in Render and run the three SQL migrations against its PostgreSQL database. Deploy `frontend/` to Vercel and set `NEXT_PUBLIC_API_URL` to the Render API URL. Set `ALLOWED_ORIGINS` on Render to the Vercel production URL. Never deploy Razorpay live keys: this project rejects any key ID that is not prefixed `rzp_test_`.
