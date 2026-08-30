"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { BreakdownMetric } from "../../types/api";
import { Card, labelize, money } from "./ui";

export function DiagnosisChart({ data }: { data?: Record<string, BreakdownMetric> }) {
  const chartData = Object.entries(data ?? {}).map(([diagnosis, metric]) => ({ name: labelize(diagnosis), attempts: metric.attempts, successful: metric.success, recovered: (metric.recovered_paise ?? 0) / 100 }));
  return <Card className="p-6"><h2 className="text-lg font-semibold">Recovery by diagnosis</h2><p className="mt-1 text-sm text-slate-400">Attempts, successful outcomes, and recovered revenue.</p>{chartData.length ? <div className="mt-5 h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ left: 8 }}><CartesianGrid stroke="#1e293b" vertical={false} /><XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} /><YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 12 }} formatter={(value, name) => name === "recovered" ? money(Number(value) * 100) : value} /><Legend /><Bar dataKey="attempts" fill="#38bdf8" radius={[4, 4, 0, 0]} /><Bar dataKey="successful" fill="#34d399" radius={[4, 4, 0, 0]} /><Bar dataKey="recovered" fill="#a78bfa" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div> : <p className="mt-8 text-sm text-slate-400">No diagnosis metrics are available for this batch.</p>}</Card>;
}
