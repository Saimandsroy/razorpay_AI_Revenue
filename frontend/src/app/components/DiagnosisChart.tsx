"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from "recharts";
import type { BreakdownMetric } from "../../types/api";
import { Card, labelize, money } from "./ui";

export function DiagnosisChart({ data }: { data?: Record<string, BreakdownMetric> }) {
  // Exclude the _batch_stats key from the chart data
  const chartData = Object.entries(data ?? {})
    .filter(([diagnosis]) => diagnosis !== "_batch_stats")
    .map(([diagnosis, metric]) => ({
      name: labelize(diagnosis),
      value: (metric.recovered_paise ?? 0) / 100,
      attempts: metric.attempts
    }))
    .filter(item => item.value > 0 || item.attempts > 0);

  const COLORS = ['#2f81f7', '#d29922', '#f85149', '#3fb950', '#8957e5'];

  return (
    <Card className="h-full flex flex-col justify-between">
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-secondary mb-1">Leakage Category Breakdown</h2>
        <p className="text-xs text-tertiary">Distribution of revenue events</p>
      </div>

      {chartData.length ? (
        <div className="mt-8 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                dataKey="attempts"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#111418", border: "1px solid #21262d", borderRadius: "4px", fontSize: "12px" }}
                itemStyle={{ color: "#e6edf3" }}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                iconType="circle"
                wrapperStyle={{ fontSize: "11px", color: "#848d97" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="mt-8 flex h-64 items-center justify-center text-xs text-tertiary font-mono">
          NO DATA AVAILABLE
        </div>
      )}
    </Card>
  );
}
