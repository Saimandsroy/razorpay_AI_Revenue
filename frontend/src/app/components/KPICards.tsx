import type { BatchSummary } from "../../types/api";
import { Card, Skeleton, money } from "./ui";

export function KPICards({ summary, loading }: { summary: BatchSummary | null; loading: boolean }) {
  const items = [
    ["Cases analyzed", summary?.cases_analyzed?.toLocaleString() ?? "—"],
    ["Revenue at risk", summary ? money(summary.revenue_at_risk_paise) : "—"],
    ["Revenue recovered", summary ? money(summary.revenue_recovered_paise) : "—"],
    ["Recovery rate", summary ? `${(summary.recovery_rate * 100).toFixed(1)}%` : "—"],
  ];
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{items.map(([label, value]) => <Card key={label} className="p-5"><p className="text-sm text-slate-400">{label}</p>{loading ? <Skeleton className="mt-3 h-8 w-28" /> : <p className="mt-2 text-2xl font-semibold text-white">{value}</p>}</Card>)}</div>;
}
