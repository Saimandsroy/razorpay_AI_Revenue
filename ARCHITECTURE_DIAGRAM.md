# SYSTEM ARCHITECTURE

## High-Level Flow

```text
Razorpay Test Mode failed payment
              |
              v
  Detection + failure normalization
              |
              v
 Root-cause diagnosis + customer context
              |
              v
 Recovery score + revenue-at-risk + priority
              |
              v
 Context-aware deterministic recommendation
              |
       +------v-------+
       | Claude (opt.)|  explanation/confidence only
       +------+-------+
              |
              v
     Deterministic policy gate
         |               |
      allowed          stopped
         |               |
         v               v
 Safe executor       Audit event
         |
         v
 Outcome tracking --> PostgreSQL cases, batches, audit events
         |
         v
 FastAPI --> Next.js dashboard and case audit timeline
```

## Key Components

### Backend (Python/FastAPI)

- Detection fetches failed Razorpay test-mode payments.
- Diagnosis maps error codes to actionable root causes.
- Scoring calculates deterministic recovery likelihood.
- Claude is an optional bounded reasoning layer with validation and fallback.
- Policy applies retry, churn, dispute, and mandate safeguards.
- Executor records safe, limited actions; outcome tracking measures results.

### Frontend (Next.js/React)

- KPI cards and performance visualization use live batch summaries.
- Recharts visualizes diagnosis and action effectiveness.
- The cases table links to full decision and audit views.

### Database (PostgreSQL)

- `recovery_batches`: aggregate metrics and breakdowns.
- `recovery_cases`: payment decisions, execution, and outcomes.
- `audit_events`: timestamped decision evidence in JSONB.

## Differentiation

1. Root-cause diagnosis, not generic retry.
2. Context-aware action selection.
3. Explicit alternative-action rejection reasoning.
4. Deterministic policy enforcement.
5. Razorpay Test Mode integration.
6. Complete auditability and recovery metrics.
7. Optional Claude reasoning with deterministic fallback.
