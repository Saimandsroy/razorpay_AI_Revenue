"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchRecoveryActionsStats } from "../../lib/api";
import type { RecoveryActionsStats } from "../../types/api";
import { Card, Skeleton, labelize, money } from "./ui";

export function RevenueImpact({ batchId }: { batchId: string | null }) {
  const [stats, setStats] = useState<RecoveryActionsStats | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!batchId) return;
    setLoading(true);
    try {
      setStats(await fetchRecoveryActionsStats(batchId));
    } catch {
      // Stats will remain null
    } finally {
      setLoading(false);
    }
  }, [batchId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!batchId) return;
    const interval = window.setInterval(() => { void load(); }, 15_000);
    return () => window.clearInterval(interval);
  }, [batchId, load]);

  if (!batchId) {
    return (
      <Card className="h-full flex flex-col justify-center text-center p-8 text-secondary">
        Start a batch to see revenue impact analysis.
      </Card>
    );
  }

  if (loading && !stats) {
    return (
      <Card className="h-full p-6">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-secondary mb-4">Financial Impact</h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
      </Card>
    );
  }

  if (!stats) return null;

  const recoveryRate = stats.revenue_at_risk_paise > 0
    ? ((stats.revenue_recovered_paise / stats.revenue_at_risk_paise) * 100).toFixed(1)
    : "0.0";
  const pendingRevenue = stats.revenue_at_risk_paise - stats.revenue_recovered_paise;

  const actionEntries = Object.entries(stats.by_action);

  return (
    <Card noPadding className="h-full flex flex-col">
      <div className="border-b border-border p-6">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-secondary mb-1">Financial Impact</h2>
        <p className="text-xs text-tertiary">
          Revenue is attributed upon confirmed payment capture.
        </p>
      </div>

      <div className="grid flex-1 grid-cols-2 gap-px border-b border-border bg-border xl:grid-cols-4">
        <div className="bg-surface px-6 py-5 flex flex-col justify-center">
          <p className="text-[10px] font-mono uppercase tracking-wider text-tertiary">Revenue at Risk</p>
          <p className="mt-1 text-2xl font-semibold text-primary">{money(stats.revenue_at_risk_paise)}</p>
        </div>
        <div className="bg-surface px-6 py-5 flex flex-col justify-center">
          <p className="text-[10px] font-mono uppercase tracking-wider text-accent-green">Revenue Recovered</p>
          <p className="mt-1 text-2xl font-semibold text-accent-green">{money(stats.revenue_recovered_paise)}</p>
        </div>
        <div className="bg-surface px-6 py-5 flex flex-col justify-center">
          <p className="text-[10px] font-mono uppercase tracking-wider text-tertiary">Recovery Rate</p>
          <p className="mt-1 text-2xl font-semibold text-primary">{recoveryRate}%</p>
        </div>
        <div className="bg-surface px-6 py-5 flex flex-col justify-center">
          <p className="text-[10px] font-mono uppercase tracking-wider text-accent-amber">Pending Recoverable</p>
          <p className="mt-1 text-2xl font-semibold text-accent-amber">{money(Math.max(0, pendingRevenue))}</p>
        </div>
      </div>

      {actionEntries.length > 0 && (
        <div className="p-6">
          <h3 className="text-[10px] font-mono font-semibold uppercase tracking-widest text-tertiary mb-4">Recovered by Action</h3>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {actionEntries.map(([actionType, metrics]) => (
              <div key={actionType} className="rounded-sm border border-border bg-background p-4">
                <p className="text-xs font-medium text-secondary truncate">{labelize(actionType)}</p>
                <div className="mt-3 flex items-end justify-between">
                  <p className="text-lg font-semibold text-accent-green">
                    {money(metrics.revenue_recovered_paise)}
                  </p>
                  <p className="text-[10px] font-mono text-tertiary">
                    {metrics.successful}/{metrics.sent} success
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
