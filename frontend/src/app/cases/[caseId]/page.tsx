"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { fetchCaseAudit, fetchCaseDetail } from "../../../lib/api";
import type { AuditEvent, CaseDetail } from "../../../types/api";
import { AuditTimeline } from "../../components/AuditTimeline";
import { Card, Skeleton, StatusBadge, labelize, money } from "../../components/ui";

export default function CaseDetailPage({ params }: { params: { caseId: string } }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [caseData, trail] = await Promise.all([fetchCaseDetail(params.caseId), fetchCaseAudit(params.caseId)]);
      setDetail(caseData); setAudit(trail);
    } catch (cause) {
      console.error("Unable to load recovery case", cause);
      setError(cause instanceof Error ? cause.message : "Could not load this recovery case.");
    } finally { setLoading(false); }
  }, [params.caseId]);

  useEffect(() => { void load(); }, [load]);
  if (loading) return <main className="mx-auto max-w-7xl px-5 py-10 sm:px-8"><Skeleton className="h-5 w-32" /><Skeleton className="mt-5 h-10 w-80" /><div className="mt-8 grid gap-6 lg:grid-cols-2"><Skeleton className="h-[32rem]" /><Skeleton className="h-[32rem]" /></div></main>;
  if (error || !detail) return <main className="mx-auto max-w-3xl px-5 py-16 sm:px-8"><Card className="border-rose-500/40 p-6"><h1 className="text-xl font-semibold">Recovery case unavailable</h1><p className="mt-3 text-sm text-rose-200">{error ?? "This case could not be found."}</p><div className="mt-6 flex gap-3"><button onClick={() => void load()} className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-bold text-slate-950">Retry</button><Link href="/dashboard" className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200">Back to dashboard</Link></div></Card></main>;

  const execution = detail.execution ?? {};
  return <main className="mx-auto max-w-7xl px-5 py-10 sm:px-8"><Link href="/dashboard" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">← Back to dashboard</Link><header className="mt-5 flex flex-col gap-3 border-b border-slate-800 pb-7 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-300">Recovery case</p><h1 className="mt-2 text-3xl font-bold text-white">{detail.customer ?? "Unknown customer"}</h1><p className="mt-2 font-mono text-xs text-slate-400">{detail.case_id}</p></div><div className="flex gap-2"><StatusBadge value={detail.status} positive={detail.status === "allowed" || detail.status === "success"} negative={detail.status === "stopped" || detail.status === "failed"} /><StatusBadge value={detail.outcome_status} positive={detail.outcome_status === "success"} negative={detail.outcome_status === "failed"} /></div></header>
    <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]"><div className="space-y-6"><Card className="p-6"><h2 className="text-lg font-semibold">Recovery decision</h2><dl className="mt-5 grid gap-5 sm:grid-cols-2"><Field label="Amount" value={money(detail.amount_paise)} /><Field label="Diagnosis" value={labelize(detail.diagnosis)} /><Field label="Recommended action" value={detail.action ? labelize(detail.action) : "Stopped"} /><Field label="Recovered amount" value={money(detail.recovered_amount_paise)} /><Field label="Policy decision" value={detail.policy_allowed ? "Allowed" : "Stopped"} /><Field label="Outcome" value={labelize(detail.outcome_status)} /></dl></Card><Card className="p-6"><h2 className="text-lg font-semibold">Policy rationale</h2><p className="mt-3 text-sm leading-6 text-slate-300">{detail.policy_reason ?? "No policy rationale was returned for this case."}</p></Card><Card className="p-6"><h2 className="text-lg font-semibold">Execution result</h2>{Object.keys(execution).length ? <pre className="mt-4 overflow-x-auto whitespace-pre-wrap break-words rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-300">{JSON.stringify(execution, null, 2)}</pre> : <p className="mt-3 text-sm text-slate-400">No execution result is available.</p>}</Card></div><AuditTimeline events={audit} /></div>
  </main>;
}

function Field({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 text-sm font-medium text-slate-100">{value}</dd></div>;
}
