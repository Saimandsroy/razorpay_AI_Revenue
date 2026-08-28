"use client";

import { useState } from "react";

type Summary = { status: string; cases_analyzed: number; revenue_at_risk_paise: number; revenue_recovered_paise: number; recovery_rate: number };
const money = (paise: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [message, setMessage] = useState("No batch selected. Start a test-mode recovery batch to populate metrics.");
  const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  async function startBatch() {
    setMessage("Starting batch…");
    try {
      const started = await fetch(`${api}/api/v1/batch/process?batch_size=50`, { method: "POST" }).then((r) => r.json());
      const data = await fetch(`${api}/api/v1/batch/${started.batch_id}/summary`).then((r) => r.json());
      setSummary(data); setMessage(`Batch ${data.status}`);
    } catch { setMessage("Could not reach the recovery API."); }
  }
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">Razorpay · Test Mode</p>
      <h1 className="mt-3 text-4xl font-bold">AI Revenue Recovery</h1>
      <p className="mt-4 max-w-2xl text-slate-300">Recovery intelligence, bounded Claude reasoning, execution audit, and batch outcome tracking.</p>
      <button onClick={startBatch} className="mt-6 rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-slate-950">Process test-mode batch</button>
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
    </main>
  );
}
