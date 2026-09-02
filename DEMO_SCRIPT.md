# RAZORPAY AI RECOVERY — 5-MINUTE DEMO SCRIPT

## System Overview (30 seconds)

Razorpay AI Revenue Recovery turns failed test-mode payments into safe, prioritized recovery cases. It identifies the root cause, combines customer-payment signals into a deterministic recovery score, and selects a context-aware action. Gemini can explain the decision, but a deterministic policy gate remains in control of what can be executed.

## Demo Flow (4.5 minutes)

### 1. Show the Dashboard (1 minute)

Open `http://localhost:3000/dashboard`.

- Point out the KPI cards for cases analyzed, revenue at risk, recovered revenue, and recovery rate.
- Show the diagnosis breakdown and recovery-action effectiveness charts.
- Show the sortable, clickable recovery cases table.

### 2. Start a Recovery Batch (2 minutes)

- Select **Process 12 test-mode payments**.
- Explain: “The system now checks Razorpay Test Mode for eligible failed payments, diagnoses each one, scores it, applies policy, and records the decision.”
- Once complete, call out the live PostgreSQL-backed KPIs, charts, and cases.

### 3. Show a Case Detail (1.5 minutes)

- Select a case from the table.
- Show its amount, diagnosis, recommended action, policy result, execution result, and outcome.
- Walk through the chronological audit timeline.
- Explain: “Every recommendation is explainable and every permitted action is bounded by deterministic policy.”

## Key Points to Emphasize

- Root-cause diagnosis means the system does more than blindly retry.
- Customer LTV, success history, inactivity, and churn signal influence the recommendation.
- Gemini provides optional reasoning only; it cannot override policy or execute financial actions.
- PostgreSQL audit events make each decision inspectable and measurable.

## If Data Is Empty (Backup Script)

If the Razorpay test account has no eligible failed payments, show the dashboard’s empty state and say: “There is currently zero revenue at risk, so the system correctly does not invent recoveries.” Then use `ARCHITECTURE_DIAGRAM.md` to walk through the production pipeline and mention the deterministic verification suite.
