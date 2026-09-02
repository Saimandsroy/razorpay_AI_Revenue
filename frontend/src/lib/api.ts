import type { AuditEvent, BatchStart, BatchSummary, CaseDetail, CaseListItem } from "../types/api";

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

export function startDemoBatch() {
  return request<BatchStart>("/api/v1/demo/batch", { method: "POST" });
}

export function fetchBatchSummary(batchId: string) {
  return request<BatchSummary>(`/api/v1/batch/${batchId}/summary`);
}

export function fetchBatchCases(batchId: string) {
  return request<CaseListItem[]>(`/api/v1/batch/${batchId}/cases?sort=amount_desc`);
}

export function fetchCaseDetail(caseId: string) {
  return request<CaseDetail>(`/api/v1/cases/${caseId}/full`);
}

export function fetchCaseAudit(caseId: string) {
  return request<AuditEvent[]>(`/api/v1/cases/${caseId}/audit`);
}
