"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { fetchBatchCases, fetchBatchSummary, fetchLiveSession, startBatch, startDemoBatch } from "../../lib/api";
import type { BatchSummary, CaseListItem } from "../../types/api";
import { ActionChart } from "../components/ActionChart";
import { CasesTable } from "../components/CasesTable";
import { DiagnosisChart } from "../components/DiagnosisChart";
import { KPICards } from "../components/KPICards";
import { RecoveryActionsSection } from "../components/RecoveryActionsSection";
import { RecoveryPerformance } from "../components/RecoveryPerformance";
import { RevenueImpact } from "../components/RevenueImpact";
import { SimulatorController } from "../components/SimulatorController";
import { Card, StatusBadge } from "../components/ui";

function DashboardContent() {
  const searchParams = useSearchParams();
  const urlBatchId = searchParams.get("batchId");

  const [batchId, setBatchId] = useState<string | null>(urlBatchId);
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
      await loadBatch(started.batch_id, true);
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
      // Update the URL so the batch ID is bookmarkable
      window.history.replaceState(null, "", `/dashboard?batchId=${started.batch_id}`);
      await loadBatch(started.batch_id, true);
    } catch (cause) {
      console.error("Unable to start simulator batch", cause);
      setError(cause instanceof Error ? cause.message : "Could not start the simulator batch.");
    } finally { setLoading(false); }
  };

  const loadLiveSession = async () => {
    setLoading(true); setError(null);
    try {
      const session = await fetchLiveSession();
      setBatchId(session.batch_id);
      await loadBatch(session.batch_id, true);
    } catch (cause) {
      console.error("Unable to load live session", cause);
      setError(cause instanceof Error ? cause.message : "Could not load live session.");
    } finally { setLoading(false); }
  };

  // Initial load
  useEffect(() => {
    if (urlBatchId) {
      void loadBatch(urlBatchId, true);
    } else {
      void loadLiveSession();
    }
  }, [urlBatchId, loadBatch]);

  // Polling
  useEffect(() => {
    if (!batchId) return;
    const interval = window.setInterval(() => { void loadBatch(batchId); }, 10_000);
    return () => window.clearInterval(interval);
  }, [batchId, loadBatch]);

  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <header className="mb-8 flex flex-col gap-5 border-b border-border pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-semibold tracking-tight text-primary">Command Center</h1>
            {summary && <StatusBadge value={summary.status === "complete" ? "Operational" : summary.status} variant={summary.status === "complete" ? "success" : "info"} />}
          </div>
          <p className="text-sm text-secondary">
            Live operations, policy safeguards, and recovery interventions.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            disabled={loading}
            onClick={handleDemoStart}
            className="rounded-md border border-accent-blue/30 bg-accent-blue/10 px-4 py-2 text-xs font-semibold text-accent-blue transition hover:bg-accent-blue/20 disabled:opacity-50"
          >
            {loading ? "Running..." : "Run Safe Demo"}
          </button>
          <button
            disabled={loading}
            onClick={handleStart}
            className="rounded-md bg-accent-blue px-4 py-2 text-xs font-semibold text-background transition hover:bg-accent-blue/90 disabled:opacity-50"
          >
            Process 12 Payments
          </button>
        </div>
      </header>

      {error && (
        <Card className="mb-6 border-accent-red/40 !bg-accent-red/5 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-accent-red">{error}</p>
            {batchId && (
              <button onClick={() => void loadBatch(batchId, true)} className="rounded bg-accent-red/20 px-3 py-1 text-xs font-semibold text-accent-red">
                Retry Connection
              </button>
            )}
          </div>
        </Card>
      )}

      {batchId && (
        <div className="mb-6 flex items-center justify-between text-xs text-secondary font-mono bg-surface border border-border px-4 py-2 rounded-sm shadow-sm">
          <div className="flex items-center gap-3">
            <span className="text-tertiary uppercase tracking-wider">Session</span>
            <span className="text-primary">{batchId}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-accent-green animate-pulse"></div>
            <span>LIVE SYNC</span>
          </div>
        </div>
      )}

      {batchId && summary && (
        <SimulatorController
          batchId={batchId}
          status={summary.status}
          onUpdate={() => void loadBatch(batchId, true)}
        />
      )}

      <div className="space-y-6">
        <section><KPICards summary={summary} loading={loading} /></section>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section><RecoveryPerformance summary={summary} /></section>
          <section><RevenueImpact batchId={batchId} /></section>
        </div>

        <section className="grid gap-6 xl:grid-cols-2">
          <DiagnosisChart data={summary?.by_diagnosis} />
          <ActionChart data={summary?.by_action} />
        </section>

        <section><CasesTable cases={cases} loading={loading} /></section>
        <section><RecoveryActionsSection batchId={batchId} /></section>
      </div>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="p-8 text-secondary">Initializing Command Center...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
