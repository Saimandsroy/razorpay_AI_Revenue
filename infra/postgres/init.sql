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
  revenue_at_risk_paise INTEGER NOT NULL DEFAULT 0,
  expected_recovery_value_paise INTEGER NOT NULL DEFAULT 0,
  recovery_priority TEXT,
  gateway_identifier TEXT,
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

CREATE TABLE recovery_actions (
  id UUID PRIMARY KEY,
  case_id UUID NOT NULL REFERENCES recovery_cases(id) ON DELETE CASCADE,
  action_type TEXT NOT NULL,
  channel TEXT NOT NULL DEFAULT 'internal',
  status TEXT NOT NULL DEFAULT 'pending',
  recipient TEXT,
  provider TEXT,
  provider_reference TEXT,
  action_url TEXT,
  amount_paise INTEGER NOT NULL DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  sent_at TIMESTAMPTZ,
  clicked_at TIMESTAMPTZ,
  responded_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  revenue_recovered_paise INTEGER NOT NULL DEFAULT 0,
  failure_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_recovery_cases_batch_id ON recovery_cases(batch_id);
CREATE INDEX idx_audit_events_case_id_created_at ON audit_events(case_id, created_at);
CREATE INDEX idx_recovery_actions_case_id ON recovery_actions(case_id);
CREATE INDEX idx_recovery_actions_status ON recovery_actions(status);
CREATE INDEX idx_recovery_actions_action_type ON recovery_actions(action_type);
CREATE INDEX idx_recovery_actions_created_at ON recovery_actions(created_at);
CREATE UNIQUE INDEX idx_recovery_actions_provider_ref ON recovery_actions(provider_reference) WHERE provider_reference IS NOT NULL;
