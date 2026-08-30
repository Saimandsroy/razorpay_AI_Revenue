"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { BreakdownMetric } from "../../types/api";
import { Card, labelize } from "./ui";

const colors = ["#38bdf8", "#34d399", "#a78bfa", "#fbbf24", "#fb7185"];

export function ActionChart({ data }: { data?: Record<string, BreakdownMetric> }) {
  const chartData = Object.entries(data ?? {}).map(([action, metric]) => ({ name: labelize(action), successRate: Number((metric.rate * 100).toFixed(1)), attempts: metric.attempts }));
  return <Card className="p-6"><h2 className="text-lg font-semibold">Recovery by action</h2><p className="mt-1 text-sm text-slate-400">Success rate across executed or proposed recovery actions.</p>{chartData.length ? <div className="mt-5 h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ left: 0 }}><CartesianGrid stroke="#1e293b" vertical={false} /><XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} /><YAxis unit="%" domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 11 }} /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 12 }} formatter={(value, _name, item) => [`${value}%`, `Success rate · ${item.payload.attempts} attempts`]} /><Bar dataKey="successRate" radius={[4, 4, 0, 0]}>{chartData.map((item, index) => <Cell key={item.name} fill={colors[index % colors.length]} />)}</Bar></BarChart></ResponsiveContainer></div> : <p className="mt-8 text-sm text-slate-400">No action metrics are available for this batch.</p>}</Card>;
}
