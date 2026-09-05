"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { fetchRecoveryActions, fetchRecoveryActionsStats } from "../../lib/api";
import type { RecoveryActionListItem, RecoveryActionsStats } from "../../types/api";
import { Card, Skeleton, formatTime, labelize, money } from "./ui";

const statusStyles: Record<string, string> = {
  completed: "border-accent-green/30 bg-accent-green/10 text-accent-green",
  failed: "border-accent-red/30 bg-accent-red/10 text-accent-red",
  clicked: "border-accent-amber/30 bg-accent-amber/10 text-accent-amber",
  accepted: "border-accent-amber/30 bg-accent-amber/10 text-accent-amber",
  sent: "border-accent-blue/30 bg-accent-blue/10 text-accent-blue",
  delivered: "border-accent-blue/30 bg-accent-blue/10 text-accent-blue",
  proposed: "border-border bg-background text-secondary",
  stopped: "border-accent-red/30 bg-accent-red/10 text-accent-red",
};

export function RecoveryActionsSection({ batchId }: { batchId: string | null }) {
  const [actions, setActions] = useState<RecoveryActionListItem[]>([]);
  const [stats, setStats] = useState<RecoveryActionsStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!batchId) return;
    setLoading(true); setError(null);
    try {
      const [nextActions, nextStats] = await Promise.all([
        fetchRecoveryActions({ batch_id: batchId }),
        fetchRecoveryActionsStats(batchId),
      ]);
      setActions(nextActions);
      setStats(nextStats);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load recovery actions.");
    } finally { setLoading(false); }
  }, [batchId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!batchId) return;
    const interval = window.setInterval(() => { void load(); }, 15_000);
    return () => window.clearInterval(interval);
  }, [batchId, load]);

  if (!batchId) {
    return (
      <Card className="flex flex-col justify-center text-center p-8 text-secondary">
        Start a batch to see recovery actions.
      </Card>
    );
  }

  return (
    <Card noPadding className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-6 py-5">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-primary mb-1">Recent Recovery Actions</h2>
          <p className="text-xs text-tertiary">Individual recovery actions sent to customers. Revenue is only counted upon confirmed payment capture.</p>
        </div>
        <Link href="/actions" className="flex items-center gap-1 text-[11px] text-accent-blue hover:text-primary transition">
          View all <ArrowUpRight size={13} />
        </Link>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-3 gap-px border-b border-border bg-border xl:grid-cols-6">
          {([
            ["Total Sent", stats.total_sent.toString()],
            ["Successful", stats.successful.toString()],
            ["Pending", stats.pending.toString()],
            ["Failed", stats.failed.toString()],
            ["Revenue Recovered", money(stats.revenue_recovered_paise)],
            ["Revenue at Risk", money(stats.revenue_at_risk_paise)],
          ] as const).map(([label, value]) => (
            <div key={label} className="bg-surface px-5 py-4">
              <p className="text-[10px] font-mono uppercase tracking-wider text-tertiary">{label}</p>
              <p className="mt-1 text-xl font-semibold text-primary">{value}</p>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="border-b border-accent-red/30 bg-accent-red/5 px-6 py-3 text-sm text-accent-red">
          {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-[860px] w-full text-left text-sm">
          <thead className="bg-background text-[10px] uppercase tracking-widest text-secondary border-b border-border">
            <tr>
              <th className="px-6 py-4 font-semibold">Customer</th>
              <th className="px-6 py-4 font-semibold">Action</th>
              <th className="px-6 py-4 font-semibold">Channel</th>
              <th className="px-6 py-4 font-semibold">Sent</th>
              <th className="px-6 py-4 font-semibold">Status</th>
              <th className="px-6 py-4 font-semibold text-right">Recovered</th>
            </tr>
          </thead>
          <tbody>
            {loading ? Array.from({ length: 3 }).map((_, i) => (
              <tr key={i} className="border-b border-border/50">
                <td colSpan={6} className="px-6 py-5">
                  <Skeleton className="h-4 w-full" />
                </td>
              </tr>
            )) : actions.map((item) => (
              <tr key={item.id} className="border-b border-border/50 transition hover:bg-surfaceHover">
                <td className="px-6 py-4">
                  <Link href={`/cases/${item.case_id}`} className="font-medium text-primary hover:text-accent-blue transition">
                    {item.customer ?? "Unknown customer"}
                  </Link>
                </td>
                <td className="px-6 py-4 text-accent-blue">{labelize(item.action_type)}</td>
                <td className="px-6 py-4 text-secondary font-mono text-[11px] uppercase tracking-wider">{labelize(item.channel)}</td>
                <td className="px-6 py-4 text-[11px] font-mono text-tertiary">{formatTime(item.sent_at)}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${statusStyles[item.status] ?? statusStyles.proposed}`}>
                    {labelize(item.status)}
                  </span>
                </td>
                <td className="px-6 py-4 text-right font-semibold text-accent-green">
                  {item.revenue_recovered_paise > 0 ? money(item.revenue_recovered_paise) : "₹0"}
                </td>
              </tr>
            ))}
            {!loading && !actions.length && (
              <tr>
                <td colSpan={6} className="px-6 py-16 text-center text-secondary text-sm">
                  No recovery actions yet. Actions are created when the pipeline executes recovery decisions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
