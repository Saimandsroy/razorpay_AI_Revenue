import type { BatchSummary } from "../../types/api";
import { Card, money } from "./ui";

export function RecoveryPerformance({ summary }: { summary: BatchSummary | null }) {
  if (!summary) return <Card className="p-6 text-sm text-slate-400">Select or start a batch to view recovery performance.</Card>;
  const percentage = Math.max(0, Math.min(100, summary.recovery_rate * 100));
  return <Card className="p-6"><div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-sm font-medium text-slate-400">Revenue at risk</p><p className="mt-1 text-3xl font-semibold">{money(summary.revenue_at_risk_paise)}</p></div><div className="sm:text-right"><p className="text-sm font-medium text-emerald-300">Revenue recovered</p><p className="mt-1 text-3xl font-semibold text-emerald-300">{money(summary.revenue_recovered_paise)} <span className="text-lg">({percentage.toFixed(1)}%)</span></p></div></div><div className="mt-6 h-3 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-emerald-400 transition-all" style={{ width: `${percentage}%` }} /></div></Card>;
}
