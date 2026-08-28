"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Summary = { status: string; cases_analyzed: number; revenue_at_risk_paise: number; revenue_recovered_paise: number; recovery_rate: number };
type Breakdown = Record<string, { attempts: number; success: number; rate: number; recovered_paise?: number }>;
type CaseItem = { case_id: string; customer: string | null; amount_paise: number; diagnosis: string; action: string | null; status: string; recovered_amount_paise: number };
type FullSummary = Summary & { by_diagnosis: Breakdown; by_action: Breakdown };
const money = (paise: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

export default function DashboardPage() {
  const [summary, setSummary] = useState<FullSummary | null>(null);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("No batch selected. Start a test-mode recovery batch to populate metrics.");
  const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  async function startBatch() {
    setMessage("Starting batch…"); setLoading(true);
    try {
      const started = await fetch(`${api}/api/v1/batch/process?batch_size=50`, { method: "POST" }).then((r) => r.json());
      const data = await fetch(`${api}/api/v1/batch/${started.batch_id}/summary`).then((r) => r.json());
      const list = await fetch(`${api}/api/v1/batch/${started.batch_id}/cases?sort=amount_desc`).then((r) => r.json());
      setCases(list);
      setSummary(data); setBatchId(started.batch_id); setMessage(`Batch ${data.status}`);
    } catch { setMessage("Could not reach the recovery API."); } finally { setLoading(false); }
  }
  useEffect(() => {
    if (!batchId) return;
    const refresh = () => Promise.all([fetch(`${api}/api/v1/batch/${batchId}/summary`), fetch(`${api}/api/v1/batch/${batchId}/cases?sort=amount_desc`)]).then(async ([summaryResponse, casesResponse]) => { if (!summaryResponse.ok || !casesResponse.ok) throw new Error("refresh failed"); setSummary(await summaryResponse.json()); setCases(await casesResponse.json()); setMessage("Batch refreshed"); }).catch(() => setMessage("Could not refresh batch status."));
    const interval = window.setInterval(refresh, 10_000); return () => window.clearInterval(interval);
  }, [api, batchId]);
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">Razorpay · Test Mode</p>
      <h1 className="mt-3 text-4xl font-bold">AI Revenue Recovery</h1>
      <p className="mt-4 max-w-2xl text-slate-300">Recovery intelligence, bounded Claude reasoning, execution audit, and batch outcome tracking.</p>
      <button disabled={loading} onClick={startBatch} className="mt-6 rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60">{loading ? "Starting…" : "Process test-mode batch"}</button>
      <p className="mt-3 text-sm text-slate-400">{message}</p>
      <section className="mt-10 grid gap-4 sm:grid-cols-3">
        {[["Revenue at risk", summary ? money(summary.revenue_at_risk_paise) : "—"], ["Recovered", summary ? money(summary.revenue_recovered_paise) : "—"], ["Cases analyzed", summary?.cases_analyzed?.toString() ?? "0"]].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-700 bg-slate-900 p-5"><p className="text-sm text-slate-400">{label}</p><p className="mt-2 text-3xl font-semibold">{value}</p></div>
        ))}
      </section>
      <section className="mt-8 rounded-xl border border-slate-700 bg-slate-900 p-6">
        <h2 className="text-lg font-semibold">Batch status</h2>
        <p className="mt-3 text-slate-300">{summary ? `${summary.status.toUpperCase()} · ${(summary.recovery_rate * 100).toFixed(0)}% recovery rate` : "Awaiting a batch."}</p>
      </section>
      <section className="mt-8 grid gap-6 lg:grid-cols-2">
        <BreakdownCard title="Recovery by diagnosis" data={summary?.by_diagnosis} recovered />
        <BreakdownCard title="Recovery by action" data={summary?.by_action} />
      </section>
      <section className="mt-8 overflow-hidden rounded-xl border border-slate-700 bg-slate-900">
        <div className="border-b border-slate-700 p-6"><h2 className="text-lg font-semibold">Cases</h2><p className="mt-1 text-sm text-slate-400">Sorted by amount; select a case to inspect its audit timeline.</p></div>
        <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-800 text-slate-400"><tr><th className="p-4">Customer</th><th className="p-4">Amount</th><th className="p-4">Diagnosis</th><th className="p-4">Action</th><th className="p-4">Status</th></tr></thead><tbody>{cases.map((item) => <tr key={item.case_id} className="border-t border-slate-800 hover:bg-slate-800/60"><td className="p-4"><Link className="text-cyan-300 hover:underline" href={`/cases/${item.case_id}`}>{item.customer ?? "Unknown"}</Link></td><td className="p-4">{money(item.amount_paise)}</td><td className="p-4">{item.diagnosis}</td><td className="p-4">{item.action ?? "—"}</td><td className="p-4">{item.status}</td></tr>)}{!cases.length && <tr><td className="p-6 text-slate-400" colSpan={5}>No cases in this batch yet.</td></tr>}</tbody></table></div>
      </section>
    </main>
  );
}

function BreakdownCard({ title, data, recovered = false }: { title: string; data?: Breakdown; recovered?: boolean }) {
  return <section className="rounded-xl border border-slate-700 bg-slate-900 p-6"><h2 className="text-lg font-semibold">{title}</h2><div className="mt-4 space-y-3">{data && Object.entries(data).map(([name, metric]) => <div key={name} className="rounded-lg bg-slate-800 p-3"><div className="flex justify-between"><span className="font-medium">{name}</span><span>{(metric.rate * 100).toFixed(0)}%</span></div><p className="mt-1 text-sm text-slate-400">{metric.success}/{metric.attempts} successful{recovered && ` · ${money(metric.recovered_paise ?? 0)} recovered`}</p></div>)}{!data && <p className="text-sm text-slate-400">Awaiting batch data.</p>}</div></section>;
}
