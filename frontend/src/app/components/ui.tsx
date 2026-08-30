import type { ReactNode } from "react";

export const money = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

export const labelize = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

export const formatTime = (value: string | null) =>
  value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-slate-800 bg-slate-900/70 shadow-sm ${className}`}>{children}</section>;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-slate-800 ${className}`} />;
}

export function StatusBadge({ value, positive, negative }: { value: string; positive?: boolean; negative?: boolean }) {
  const color = positive ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : negative ? "border-rose-500/30 bg-rose-500/10 text-rose-300" : "border-slate-700 bg-slate-800 text-slate-300";
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${color}`}>{labelize(value)}</span>;
}
