"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { BreakdownMetric } from "../../types/api";
import { Card, labelize } from "./ui";

const COLORS = ['#2f81f7', '#3fb950', '#8957e5', '#d29922', '#f85149'];

export function ActionChart({ data }: { data?: Record<string, BreakdownMetric> }) {
  const chartData = Object.entries(data ?? {})
    .filter(([action]) => action !== "_batch_stats")
    .map(([action, metric]) => ({
      name: labelize(action),
      successRate: Number((metric.rate * 100).toFixed(1)),
      attempts: metric.attempts
    }))
    .filter(item => item.attempts > 0);

  return (
    <Card className="h-full flex flex-col justify-between">
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-secondary mb-1">Action Success Rate</h2>
        <p className="text-xs text-tertiary">Performance of executed AI interventions</p>
      </div>

      {chartData.length ? (
        <div className="mt-8 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ left: -20, bottom: 0 }}>
              <CartesianGrid stroke="#21262d" vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                tick={{ fill: "#848d97", fontSize: 10 }}
                axisLine={{ stroke: "#21262d" }}
                tickLine={false}
              />
              <YAxis
                unit="%"
                domain={[0, 100]}
                tick={{ fill: "#848d97", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ background: "#111418", border: "1px solid #21262d", borderRadius: "4px", fontSize: "12px" }}
                itemStyle={{ color: "#e6edf3" }}
                cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                formatter={(value, _name, item) => [`${value}%`, `Success rate (${item.payload.attempts} attempts)`]}
              />
              <Bar dataKey="successRate" radius={[2, 2, 0, 0]} maxBarSize={40}>
                {chartData.map((item, index) => (
                  <Cell key={item.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
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
