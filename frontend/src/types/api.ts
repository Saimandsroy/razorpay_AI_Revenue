export type BreakdownMetric = {
  attempts: number;
  success: number;
  rate: number;
  recovered_paise?: number;
};

export type BatchSummary = {
  batch_id: string;
  status: string;
  cases_analyzed: number;
  revenue_at_risk_paise: number;
  revenue_recovered_paise: number;
  recovery_rate: number;
  by_diagnosis: Record<string, BreakdownMetric>;
  by_action: Record<string, BreakdownMetric>;
};

export type BatchStart = {
  batch_id: string;
  status: string;
  created_at: string | null;
  cases_count: number;
};

export type CaseListItem = {
  case_id: string;
  customer: string | null;
  amount_paise: number;
  diagnosis: string;
  action: string | null;
  status: string;
  recovered_amount_paise: number;
};

export type CaseDetail = {
  case_id: string;
  customer: string | null;
  amount_paise: number;
  diagnosis: string;
  action: string | null;
  status: string;
  recovered_amount_paise: number;
  policy_allowed: boolean | null;
  policy_reason: string | null;
  execution: Record<string, unknown> | null;
  outcome_status: string;
};

export type AuditEvent = {
  event_type: string;
  timestamp: string | null;
  data: Record<string, unknown>;
};
