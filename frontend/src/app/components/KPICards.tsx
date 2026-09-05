import type { BatchSummary } from "../../types/api";
import { Card, Skeleton, money } from "./ui";

export function KPICards({ summary, loading }: { summary: BatchSummary | null; loading: boolean }) {
  // Use _batch_stats if available (from our new batch_processor observability fix)
  const batchStats = summary?.by_diagnosis?.["_batch_stats"] as Record<string, any> | undefined;

  const items = [
    {
      label: "REVENUE AT RISK",
      value: summary ? money(summary.revenue_at_risk_paise) : "—",
      subtext: "Total leakage across all events",
      color: "border-t-accent-red"
    },
    {
      label: "EXPECTED RECOVERABLE",
      value: summary ? money(summary.expected_recovery_value_paise) : "—",
      subtext: "ML probability-weighted estimate",
      color: "border-t-accent-blue"
    },
    {
      label: "ACTUAL REVENUE RECOVERED",
      value: summary ? money(summary.revenue_recovered_paise) : "—",
      subtext: "Stochastic outcome (live)",
      color: "border-t-accent-green"
    },
    {
      label: "ACTIVE PIPELINE CASES",
      value: batchStats ? batchStats.new_cases_created : (summary?.cases_analyzed ?? "—"),
      subtext: "In-flight recovery pipeline",
      color: "border-t-accent-amber"
    }
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item, idx) => (
        <Card key={idx} className={`border-t-[3px] ${item.color} p-5 flex flex-col justify-between`}>
          <div>
            <h3 className="text-[11px] font-bold tracking-widest text-secondary mb-1">
              {item.label}
            </h3>
            {loading ? (
              <Skeleton className="mt-2 h-8 w-28" />
            ) : (
              <p className="text-3xl font-semibold tracking-tight text-primary mt-1">
                {item.value}
              </p>
            )}
          </div>
          <p className="text-xs text-tertiary mt-4">{item.subtext}</p>
        </Card>
      ))}
    </div>
  );
}
