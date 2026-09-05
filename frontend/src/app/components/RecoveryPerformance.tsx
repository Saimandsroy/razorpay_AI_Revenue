import type { BatchSummary } from "../../types/api";
import { Card, money } from "./ui";

export function RecoveryPerformance({ summary }: { summary: BatchSummary | null }) {
  if (!summary) {
    return (
      <Card className="h-full flex flex-col justify-center text-center p-8 text-secondary">
        Select or start a batch to view recovery performance.
      </Card>
    );
  }

  const percentage = Math.max(0, Math.min(100, summary.revenue_at_risk_paise > 0 ? (summary.revenue_recovered_paise / summary.revenue_at_risk_paise) * 100 : 0));

  return (
    <Card className="h-full flex flex-col justify-between">
      <div className="mb-8">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-secondary mb-1">Comparative Revenue Recovered</h2>
        <p className="text-xs text-tertiary mb-6">AI Agent vs Baseline Strategies</p>

        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-tertiary">Revenue at risk</p>
            <p className="mt-1 text-2xl font-semibold text-primary">{money(summary.revenue_at_risk_paise)}</p>
          </div>
          <div className="sm:text-right">
            <p className="text-[10px] font-mono uppercase tracking-wider text-accent-green">Revenue recovered</p>
            <p className="mt-1 text-2xl font-semibold text-accent-green">
              {money(summary.revenue_recovered_paise)} <span className="text-sm font-medium">({percentage.toFixed(1)}%)</span>
            </p>
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between text-[10px] font-mono text-tertiary mb-2">
          <span>0%</span>
          <span>100%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-sm bg-border">
          <div className="h-full rounded-sm bg-accent-green transition-all duration-1000 ease-out" style={{ width: `${percentage}%` }} />
        </div>
      </div>
    </Card>
  );
}
