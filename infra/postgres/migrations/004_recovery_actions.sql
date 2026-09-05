-- Migration: Add recovery_actions table for normalized action tracking
-- Tracks individual recovery actions, their delivery, customer interactions, and payment outcomes.

CREATE TABLE IF NOT EXISTS recovery_actions (
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

CREATE INDEX IF NOT EXISTS idx_recovery_actions_case_id ON recovery_actions(case_id);
CREATE INDEX IF NOT EXISTS idx_recovery_actions_status ON recovery_actions(status);
CREATE INDEX IF NOT EXISTS idx_recovery_actions_action_type ON recovery_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_recovery_actions_created_at ON recovery_actions(created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_recovery_actions_provider_ref ON recovery_actions(provider_reference) WHERE provider_reference IS NOT NULL;
