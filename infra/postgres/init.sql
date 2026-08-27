CREATE TYPE case_status AS ENUM ('detected', 'processing', 'allowed', 'stopped', 'pending', 'success', 'failed');
CREATE TYPE recovery_action AS ENUM ('retry', 'send_card_update_link', 'send_payment_plan', 'send_downgrade_offer', 'stop');

CREATE TABLE recovery_batches (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE recovery_cases (
  id UUID PRIMARY KEY,
  batch_id UUID REFERENCES recovery_batches(id),
  razorpay_payment_id TEXT UNIQUE NOT NULL,
  customer_id TEXT,
  customer_name TEXT,
  amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
  currency TEXT NOT NULL DEFAULT 'INR',
  error_code TEXT,
  diagnosis TEXT NOT NULL,
  recovery_score NUMERIC(4,3),
  recommended_action recovery_action,
  policy_allowed BOOLEAN,
  policy_reason TEXT,
  status case_status NOT NULL DEFAULT 'detected',
  recovered_amount_paise INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE audit_events (
  id UUID PRIMARY KEY,
  case_id UUID NOT NULL REFERENCES recovery_cases(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  message TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_recovery_cases_batch_id ON recovery_cases(batch_id);
CREATE INDEX idx_audit_events_case_id_created_at ON audit_events(case_id, created_at);
