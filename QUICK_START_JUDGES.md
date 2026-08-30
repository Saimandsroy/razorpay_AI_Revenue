# QUICK START FOR JUDGES

## Prerequisites

- Docker Desktop running.
- PostgreSQL started with the project Compose file (host port `5433`).
- A `.env` file containing Razorpay **test-mode** credentials. Claude is optional.

## Start the System

Terminal 1:

```bash
cd razorpay-recovery
docker compose up -d db
cd backend
.venv/bin/python -m uvicorn app.main:app --reload --host localhost --port 8000
```

Terminal 2:

```bash
cd razorpay-recovery/frontend
npm install
npm run dev -- --hostname localhost --port 3000
```

## Access Dashboard

Open `http://localhost:3000/dashboard` (use `localhost`, not `127.0.0.1`). Select **Process 12 test-mode payments** to create a recovery batch. The dashboard auto-refreshes the summary and cases every ten seconds.

## View a Case

Select a case from the table to view its payment amount, diagnosis, recommended action, policy rationale, execution result, outcome, and chronological audit trail.

## Stop the System

Press `Ctrl+C` in the backend and frontend terminals. PostgreSQL can remain running for the next demo.

## Test Data Note

If the Razorpay Test Mode account has no eligible failed payments, the dashboard will show empty states. This is expected and demonstrates that the system does not fabricate revenue risk or recoveries.
