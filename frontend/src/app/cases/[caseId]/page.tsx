"use client";

import { useEffect, useState } from "react";

type CaseData = { customer: string | null; amount_paise: number; diagnosis: string; action: string | null; status: string; recovered_amount_paise: number; policy_reason: string; outcome_status: string };
type Audit = { event_type: string; timestamp: string | null; data: Record<string, unknown> };
const money = (paise: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

export default function CaseDetail({ params }: { params: { caseId: string } }) {
  const [data, setData] = useState<CaseData | null>(null); const [audit, setAudit] = useState<Audit[]>([]);
  useEffect(() => { const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"; Promise.all([fetch(`${api}/api/v1/cases/${params.caseId}/full`).then((r) => r.json()), fetch(`${api}/api/v1/cases/${params.caseId}/audit`).then((r) => r.json())]).then(([caseData, trail]) => { setData(caseData); setAudit(trail); }); }, [params.caseId]);
  if (!data) return <main className="mx-auto max-w-4xl px-6 py-16 text-slate-300">Loading recovery case…</main>;
  return <main className="mx-auto max-w-4xl px-6 py-16"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">Recovery case</p><h1 className="mt-3 text-3xl font-bold">{data.customer ?? "Unknown customer"} · {money(data.amount_paise)}</h1><section className="mt-8 grid gap-4 sm:grid-cols-2">{[["Diagnosis", data.diagnosis], ["Action", data.action ?? "Stopped"], ["Outcome", data.outcome_status], ["Recovered", money(data.recovered_amount_paise)]].map(([label, value]) => <div key={label} className="rounded-xl border border-slate-700 bg-slate-900 p-5"><p className="text-sm text-slate-400">{label}</p><p className="mt-2 font-semibold">{value}</p></div>)}</section><p className="mt-5 rounded-lg border border-slate-700 p-4 text-slate-300">Policy: {data.policy_reason}</p><section className="mt-8"><h2 className="text-xl font-semibold">Audit trail</h2><ol className="mt-4 space-y-3">{audit.map((item, index) => <li key={`${item.event_type}-${index}`} className="rounded-lg border border-slate-700 bg-slate-900 p-4"><p className="font-medium text-cyan-300">{item.event_type}</p><p className="mt-1 text-sm text-slate-400">{item.timestamp ?? "Pending"}</p></li>)}</ol></section></main>;
}
