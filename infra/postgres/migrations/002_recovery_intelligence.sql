ALTER TABLE recovery_cases
  ADD COLUMN IF NOT EXISTS revenue_at_risk_paise INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS expected_recovery_value_paise INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS recovery_priority TEXT,
  ADD COLUMN IF NOT EXISTS gateway_identifier TEXT;

CREATE INDEX IF NOT EXISTS idx_recovery_cases_priority ON recovery_cases(recovery_priority);
CREATE INDEX IF NOT EXISTS idx_recovery_cases_gateway ON recovery_cases(gateway_identifier);
