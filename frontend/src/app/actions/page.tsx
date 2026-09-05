"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { RefreshCw, FlaskConical, ArrowRight } from "lucide-react";
import { fetchRecoveryActions, fetchRecoveryActionsStats } from "../../lib/api";
import type { RecoveryActionListItem, RecoveryActionsStats } from "../../types/api";
import { Card, Skeleton, formatTime, labelize, money } from "../components/ui";

const statusStyles: Record<string, string> = {
  completed: "border-accent-green/30 bg-accent-green/10 text-accent-green",
  failed: "border-accent-red/30 bg-accent-red/10 text-accent-red",
  clicked: "border-accent-amber/30 bg-accent-amber/10 text-accent-amber",
  accepted: "border-accent-amber/30 bg-accent-amber/10 text-accent-amber",
  sent: "border-accent-blue/30 bg-accent-blue/10 text-accent-blue",
  delivered: "border-accent-blue/30 bg-accent-blue/10 text-accent-blue",
  proposed: "border-border bg-background text-secondary",
  stopped: "border-border bg-background text-tertiary",
  cancelled: "border-border bg-background text-tertiary",
};

const STATUS_FILTERS = ["", "sent", "clicked", "accepted", "completed", "failed", "cancelled"];

const ACTION_LABELS: Record<string, string> = {
  send_card_update_link: "Card Update",
  send_payment_plan: "Payment Plan",
  send_downgrade_offer: "Downgrade Offer",
  retry: "Retry",
  stop: "Stop",
};

function ActionsContent() {
  const searchParams = useSearchParams();
  const urlBatchId = searchParams.get("batchId");

  const [actions, setActions] = useState<RecoveryActionListItem[]>([]);
  const [stats, setStats] = useState<RecoveryActionsStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = {
        ...(statusFilter && { status: statusFilter }),
        ...(urlBatchId && { batch_id: urlBatchId }),
      };
      const [data, statsData] = await Promise.all([
        fetchRecoveryActions(Object.keys(params).length ? params : undefined),
        fetchRecoveryActionsStats(urlBatchId ?? undefined),
      ]);
      setActions(data);
      setStats(statsData);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load recovery actions.");
    } finally { setLoading(false); }
  }, [statusFilter, urlBatchId]);

  useEffect(() => { void load(); }, [load]);

  const successRate = stats ? (stats.total_sent > 0 ? Math.round((stats.successful / stats.total_sent) * 100) : 0) : 0;

  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <header className="mb-8 flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-1">Recovery</div>
          <h1 className="text-2xl font-semibold text-primary">Recovery Actions</h1>
          <p className="text-xs text-secondary mt-1">All customer interventions executed by the AI recovery pipeline.</p>
        </div>
        <button onClick={() => void load()} className="flex items-center gap-2 rounded-sm border border-border bg-background px-4 py-2 text-xs font-semibold text-secondary hover:text-primary transition">
          <RefreshCw size={13} /> Refresh
        </button>
      </header>

      {/* KPI strip */}
      {stats && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-5">
          {[
            { label: "Total Actions", value: stats.total_sent.toString() },
            { label: "Successful", value: stats.successful.toString(), color: "text-accent-green" },
            { label: "Pending", value: stats.pending.toString(), color: "text-accent-amber" },
            { label: "Success Rate", value: `${successRate}%`, color: successRate > 50 ? "text-accent-green" : "text-secondary" },
            { label: "Revenue Recovered", value: money(stats.revenue_recovered_paise), color: stats.revenue_recovered_paise > 0 ? "text-accent-green" : "text-secondary" },
          ].map(({ label, value, color }) => (
            <div key={label} className="border border-border bg-surface rounded-sm p-4">
              <p className="text-[9px] font-mono uppercase tracking-widest text-tertiary">{label}</p>
              <p className={`text-xl font-semibold mt-1 ${color ?? "text-primary"}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Action type breakdown */}
      {stats && Object.keys(stats.by_action).length > 0 && (
        <div className="mb-6 border border-border bg-surface rounded-sm p-4">
          <p className="text-[9px] font-mono uppercase tracking-widest text-tertiary mb-3">By Action Type</p>
          <div className="flex flex-wrap gap-4">
            {Object.entries(stats.by_action).map(([action, data]) => (
              <div key={action} className="flex items-center gap-3 text-xs">
                <span className="text-secondary font-medium">{ACTION_LABELS[action] ?? labelize(action)}</span>
                <span className="font-mono text-tertiary">{data.sent} sent</span>
                {data.successful > 0 && <span className="font-mono text-accent-green">{data.successful} recovered</span>}
                {data.revenue_recovered_paise > 0 && <span className="font-mono text-accent-green">{money(data.revenue_recovered_paise)}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Status filters */}
      <div className="mb-4 flex gap-2 flex-wrap">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-sm border px-3 py-1 text-[10px] font-mono uppercase tracking-widest transition ${
              statusFilter === s
                ? "border-accent-blue bg-accent-blue/10 text-accent-blue"
                : "border-border text-tertiary hover:text-secondary"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      <Card noPadding className="overflow-hidden">
        {error && (
          <div className="border-b border-accent-red/30 bg-accent-red/5 px-6 py-3 text-sm text-accent-red">{error}</div>
        )}
        <div className="overflow-x-auto">
          <table className="min-w-[1100px] w-full text-left text-sm">
            <thead className="bg-background text-[9px] uppercase tracking-widest text-secondary border-b border-border">
              <tr>
                <th className="px-5 py-4 font-semibold">Customer</th>
                <th className="px-5 py-4 font-semibold">Amount</th>
                <th className="px-5 py-4 font-semibold">Action Type</th>
                <th className="px-5 py-4 font-semibold">Channel</th>
                <th className="px-5 py-4 font-semibold">Sent</th>
                <th className="px-5 py-4 font-semibold">Status</th>
                <th className="px-5 py-4 font-semibold">Response</th>
                <th className="px-5 py-4 font-semibold text-right">Recovered</th>
                <th className="px-5 py-4 font-semibold"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 6 }).map((_, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td colSpan={9} className="px-5 py-5">
                    <Skeleton className="h-4 w-full" />
                  </td>
                </tr>
              )) : actions.map((item) => {
                const isSimulation = (item as any).provider_reference?.startsWith?.("demo_capture");
                return (
                  <tr key={item.id} className="border-b border-border/50 transition hover:bg-surfaceHover">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        {isSimulation && (
                          <FlaskConical size={11} className="text-accent-amber shrink-0" />
                        )}
                        <Link href={`/cases/${item.case_id}`} className="font-medium text-primary hover:text-accent-blue transition">
                          {item.customer ?? "Unknown Customer"}
                        </Link>
                      </div>
                    </td>
                    <td className="px-5 py-4 font-mono text-[12px] text-secondary">{money(item.amount_paise)}</td>
                    <td className="px-5 py-4 text-accent-blue font-medium text-xs">{ACTION_LABELS[item.action_type] ?? labelize(item.action_type)}</td>
                    <td className="px-5 py-4 font-mono text-[10px] uppercase tracking-wider text-tertiary">{item.channel}</td>
                    <td className="px-5 py-4 text-[11px] font-mono text-tertiary">{formatTime(item.sent_at)}</td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider ${statusStyles[item.status] ?? statusStyles.proposed}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-[11px] font-mono text-tertiary">
                      {item.status === "clicked" || item.status === "accepted" ? "✓ Responded" :
                       item.status === "completed" ? "✓ Captured" :
                       item.status === "sent" ? "Awaiting" : "—"}
                    </td>
                    <td className="px-5 py-4 text-right">
                      {item.revenue_recovered_paise > 0 ? (
                        <span className="font-semibold text-accent-green">{money(item.revenue_recovered_paise)}</span>
                      ) : (
                        <span className="text-tertiary font-mono text-[11px]">—</span>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <Link href={`/cases/${item.case_id}`} className="text-tertiary hover:text-accent-blue transition">
                        <ArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {!loading && !actions.length && (
                <tr>
                  <td colSpan={9} className="px-5 py-16 text-center text-secondary text-sm">
                    No recovery actions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </main>
  );
}

export default function ActionsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-secondary">Loading Recovery Actions...</div>}>
      <ActionsContent />
    </Suspense>
  );
}
