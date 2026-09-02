"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchBatchCases, fetchBatchSummary, startBatch, startDemoBatch } from "../../lib/api";
import type { BatchSummary, CaseListItem } from "../../types/api";
import { ActionChart } from "../components/ActionChart";
import { CasesTable } from "../components/CasesTable";
import { DiagnosisChart } from "../components/DiagnosisChart";
import { KPICards } from "../components/KPICards";
import { RecoveryPerformance } from "../components/RecoveryPerformance";
import { Card, StatusBadge } from "../components/ui";

export default function DashboardPage() {
  const [batchId, setBatchId] = useState<string | null>(null);
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadBatch = useCallback(async (id: string, showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const [nextSummary, nextCases] = await Promise.all([fetchBatchSummary(id), fetchBatchCases(id)]);
      setSummary(nextSummary); setCases(nextCases); setError(null);
    } catch (cause) {
      console.error("Unable to load recovery batch", cause);
      setError(cause instanceof Error ? cause.message : "Could not load the recovery batch.");
    } finally { if (showLoading) setLoading(false); }
  }, []);

  const handleStart = async () => {
    setLoading(true); setError(null);
    try {
      const started = await startBatch(12);
      setBatchId(started.batch_id);
      await loadBatch(started.batch_id);
    } catch (cause) {
      console.error("Unable to start recovery batch", cause);
      setError(cause instanceof Error ? cause.message : "Could not start a recovery batch.");
    } finally { setLoading(false); }
  };

  const handleDemoStart = async () => {
    setLoading(true); setError(null);
    try {
      const started = await startDemoBatch();
      setBatchId(started.batch_id);
      await loadBatch(started.batch_id);
    } catch (cause) {
      console.error("Unable to start safe demo batch", cause);
      setError(cause instanceof Error ? cause.message : "Could not start the safe demo batch.");
    } finally { setLoading(false); }
  };

  useEffect(() => {
    if (!batchId) return;
    const interval = window.setInterval(() => { void loadBatch(batchId); }, 10_000);
    return () => window.clearInterval(interval);
  }, [batchId, loadBatch]);

  return <main className="mx-auto max-w-7xl px-5 py-10 sm:px-8"><header className="flex flex-col gap-5 border-b border-slate-800 pb-8 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-300">Razorpay · Test mode</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-white sm:text-4xl">Revenue Recovery Intelligence</h1><p className="mt-3 max-w-2xl text-slate-400">Operational visibility for recovery decisions, policy safeguards, and outcomes.</p></div><div className="flex flex-wrap gap-3"><button disabled={loading} onClick={handleDemoStart} className="rounded-xl border border-cyan-400/50 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60">{loading ? "Loading batch…" : "Run safe demo batch"}</button><button disabled={loading} onClick={handleStart} className="rounded-xl bg-cyan-400 px-5 py-3 text-sm font-bold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60">Process 12 test-mode payments</button></div></header>
    {error && <Card className="mt-6 border-rose-500/40 p-5"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-rose-200">{error}</p>{batchId && <button onClick={() => void loadBatch(batchId, true)} className="rounded-lg bg-rose-400/15 px-3 py-2 text-sm font-semibold text-rose-200">Retry</button>}</div></Card>}
    <Card className="mt-6 p-5"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm text-slate-400">Batch overview</p><p className="mt-1 font-mono text-sm text-slate-200">{batchId ?? "No batch selected"}</p></div>{summary ? <StatusBadge value={summary.status} positive={summary.status === "complete"} /> : <p className="text-sm text-slate-400">Start a test-mode batch to load live PostgreSQL-backed results.</p>}</div></Card>
    <section className="mt-6"><KPICards summary={summary} loading={loading} /></section>
    <section className="mt-6"><RecoveryPerformance summary={summary} /></section>
    <section className="mt-6 grid gap-6 xl:grid-cols-2"><DiagnosisChart data={summary?.by_diagnosis} /><ActionChart data={summary?.by_action} /></section>
    <section className="mt-6"><CasesTable cases={cases} loading={loading} /></section>
  </main>;
}
