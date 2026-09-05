export type BreakdownMetric = {
  attempts: number;
  success: number;
  rate: number;
  recovered_paise?: number;
};

export type GlobalAuditEvent = {
  id: string;
  event_type: string;
  case_id: string;
  payment_id: string;
  customer: string | null;
  timestamp: string | null;
  data: Record<string, unknown>;
};

export type BatchSummary = {
  batch_id: string;
  status: string;
  cases_analyzed: number;
  revenue_at_risk_paise: number;
  expected_recovery_value_paise: number;
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

export type RecoveryAction = {
  id: string;
  case_id: string;
  action_type: string;
  channel: string;
  status: string;
  recipient: string | null;
  provider: string | null;
  provider_reference: string | null;
  action_url: string | null;
  amount_paise: number;
  sent_at: string | null;
  clicked_at: string | null;
  responded_at: string | null;
  completed_at: string | null;
  revenue_recovered_paise: number;
  failure_reason: string | null;
  created_at: string | null;
};

export type RecoveryActionListItem = {
  id: string;
  case_id: string;
  customer: string | null;
  amount_paise: number;
  action_type: string;
  channel: string;
  status: string;
  recipient: string | null;
  sent_at: string | null;
  revenue_recovered_paise: number;
};

export type TimelineEvent = {
  event_type: string;
  timestamp: string | null;
  message: string;
};

export type CustomerJourney = {
  case: {
    id: string;
    payment_id: string;
    customer_name: string | null;
    customer_email: string | null;
    customer_id: string | null;
    amount_paise: number;
    diagnosis: string;
    recovery_score: number | null;
    recommended_action: string | null;
    policy_allowed: boolean | null;
    policy_reason: string | null;
    status: string;
    outcome_status: string;
    execution_status: string | null;
  };
  actions: RecoveryAction[];
  timeline: TimelineEvent[];
  revenue: {
    at_risk_paise: number;
    recovered_paise: number;
  };
};

export type RecoveryActionsStats = {
  total_sent: number;
  successful: number;
  pending: number;
  failed: number;
  revenue_recovered_paise: number;
  revenue_at_risk_paise: number;
  by_action: Record<string, { sent: number; successful: number; revenue_recovered_paise: number }>;
};

export type CaseListItemV2 = {
  case_id: string;
  customer: string | null;
  amount_paise: number;
  diagnosis: string;
  recovery_score: number | null;
  action: string | null;
  execution_status: string | null;
  status: string;
  outcome_status: string;
  recovered_amount_paise: number;
};

export type ActionEventRequest = {
  event_type: string;
  metadata?: Record<string, unknown>;
};

