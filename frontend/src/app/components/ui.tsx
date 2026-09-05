import type { ReactNode } from "react";

export const money = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

export const labelize = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

export const formatTime = (value: string | null) =>
  value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";

export function Card({ children, className = "", noPadding = false }: { children: ReactNode; className?: string; noPadding?: boolean }) {
  return (
    <section className={`border border-border bg-surface shadow-sm ${!noPadding ? "p-6" : ""} ${className}`}>
      {children}
    </section>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-border ${className}`} />;
}

export function StatusBadge({ value, variant = "default" }: { value: string; variant?: "success" | "warning" | "danger" | "default" | "info" }) {
  const styles = {
    success: "border-accent-green/30 bg-accent-green/10 text-accent-green",
    warning: "border-accent-amber/30 bg-accent-amber/10 text-accent-amber",
    danger: "border-accent-red/30 bg-accent-red/10 text-accent-red",
    info: "border-accent-blue/30 bg-accent-blue/10 text-accent-blue",
    default: "border-border bg-background text-secondary",
  };
  return (
    <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${styles[variant]}`}>
      {labelize(value)}
    </span>
  );
}
