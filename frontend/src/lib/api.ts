import type { AuditEvent, BatchStart, BatchSummary, CaseDetail, CaseListItem, CaseListItemV2, CustomerJourney, GlobalAuditEvent, RecoveryActionListItem, RecoveryActionsStats } from "../types/api";

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, init);
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // The API may return a non-JSON gateway error.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function startBatch(batchSize = 12) {
  return request<BatchStart>(`/api/v1/batch/process?batch_size=${batchSize}`, { method: "POST" });
}

export function fetchLiveSession() {
  return request<BatchStart>("/api/v1/batch/live");
}

export function startDemoBatch() {
  return request<BatchStart>("/api/v1/demo/recovery-batch", { method: "POST" });
}

export function advanceSimulatorBatch(batchId: string) {
  return request<{ status: string; cases_processed: number }>(`/api/v1/demo/batch/${batchId}/advance`, { method: "POST" });
}

export function simulateCustomerResponses(batchId: string) {
  return request<{ status: string; actions_updated: number }>(`/api/v1/demo/batch/${batchId}/simulate-responses`, { method: "POST" });
}

export function simulateRecoveries(batchId: string) {
  return request<{ status: string; recoveries: number }>(`/api/v1/demo/batch/${batchId}/simulate-recoveries`, { method: "POST" });
}

export function fetchBatchSummary(batchId: string) {
  return request<BatchSummary>(`/api/v1/batch/${batchId}/summary`);
}

export function fetchBatchCases(batchId: string) {
  return request<CaseListItem[]>(`/api/v1/batch/${batchId}/cases?sort=amount_desc`);
}

export function fetchBatchCasesV2(batchId: string) {
  return request<CaseListItemV2[]>(`/api/v1/batch/${batchId}/cases/v2?sort=amount_desc`);
}

export function fetchCaseDetail(caseId: string) {
  return request<CaseDetail>(`/api/v1/cases/${caseId}/full`);
}

export function fetchCaseAudit(caseId: string) {
  return request<AuditEvent[]>(`/api/v1/cases/${caseId}/audit`);
}

export function fetchCaseJourney(caseId: string) {
  return request<CustomerJourney>(`/api/v1/cases/${caseId}/journey`);
}

export function fetchRecoveryActions(params?: { batch_id?: string; status?: string; action_type?: string }) {
  const qs = new URLSearchParams();
  if (params?.batch_id) qs.set("batch_id", params.batch_id);
  if (params?.status) qs.set("status", params.status);
  if (params?.action_type) qs.set("action_type", params.action_type);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<RecoveryActionListItem[]>(`/api/v1/recovery-actions${suffix}`);
}

export function fetchRecoveryActionsStats(batchId?: string) {
  const qs = batchId ? `?batch_id=${batchId}` : "";
  return request<RecoveryActionsStats>(`/api/v1/recovery-actions/stats${qs}`);
}

export function postActionEvent(actionId: string, eventType: string, metadata?: Record<string, unknown>) {
  return request<{ action_id: string; status: string; event_type: string; message: string }>(
    `/api/v1/recovery-actions/${actionId}/events`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event_type: eventType, metadata: metadata ?? {} }) },
  );
}

export function fetchGlobalAudit(limit = 100, event_type?: string) {
  const qs = new URLSearchParams({ limit: limit.toString() });
  if (event_type) qs.set("event_type", event_type);
  return request<GlobalAuditEvent[]>(`/api/v1/audit?${qs.toString()}`);
}
