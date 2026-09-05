"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import type { CaseListItem } from "../../types/api";
import { Card, StatusBadge, labelize, money } from "./ui";

type SortKey = "amount" | "recovered";

export function CasesTable({ cases, loading }: { cases: CaseListItem[]; loading: boolean }) {
  const [sort, setSort] = useState<SortKey>("amount");
  const ordered = useMemo(() => [...cases].sort((a, b) => sort === "amount" ? b.amount_paise - a.amount_paise : b.recovered_amount_paise - a.recovered_amount_paise), [cases, sort]);

  return (
    <Card noPadding className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-border p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-primary mb-1">Active Revenue Recovery Cases</h2>
          <p className="text-xs text-tertiary">Real-time AI pipeline processing queue</p>
        </div>
        <div className="flex gap-2 bg-background p-1 rounded border border-border">
          <button
            className={`rounded-sm px-3 py-1 text-[10px] uppercase tracking-wider transition ${sort === "amount" ? "bg-surfaceHover font-bold text-primary shadow-sm" : "text-tertiary hover:text-secondary"}`}
            onClick={() => setSort("amount")}
          >
            Sort Amount
          </button>
          <button
            className={`rounded-sm px-3 py-1 text-[10px] uppercase tracking-wider transition ${sort === "recovered" ? "bg-surfaceHover font-bold text-primary shadow-sm" : "text-tertiary hover:text-secondary"}`}
            onClick={() => setSort("recovered")}
          >
            Sort Recovered
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1000px] w-full text-left text-sm">
          <thead className="bg-background text-[10px] uppercase tracking-widest text-secondary border-b border-border">
            <tr>
              <th className="px-6 py-4 font-semibold">Case ID</th>
              <th className="px-6 py-4 font-semibold">Customer</th>
              <th className="px-6 py-4 font-semibold">Scenario</th>
              <th className="px-6 py-4 font-semibold">Amount ₹</th>
              <th className="px-6 py-4 font-semibold">AI Intervention</th>
              <th className="px-6 py-4 font-semibold">Guardrail</th>
              <th className="px-6 py-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <tr key={index} className="border-b border-border/50">
                  <td colSpan={7} className="px-6 py-5">
                    <div className="h-4 w-full animate-pulse rounded bg-border" />
                  </td>
                </tr>
              ))
            ) : ordered.map((item) => {
              const statusVariant = item.status === "allowed" || item.status === "success" ? "success"
                                   : item.status === "stopped" || item.status === "failed" ? "danger" : "warning";

              const scenarioVariant = item.diagnosis.includes("abandonment") || item.diagnosis.includes("expired") ? "warning"
                                    : item.diagnosis.includes("failed") ? "danger" : "info";

              return (
                <tr key={item.case_id} className="border-b border-border/50 transition hover:bg-surfaceHover">
                  <td className="px-6 py-4 font-mono text-[11px] text-secondary">
                    {item.case_id.split("-")[0]}
                  </td>
                  <td className="px-6 py-4 font-medium text-primary">
                    {item.customer ?? "Unknown customer"}
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge value={item.diagnosis} variant={scenarioVariant} />
                  </td>
                  <td className="px-6 py-4 font-mono text-primary">
                    {money(item.amount_paise)}
                  </td>
                  <td className="px-6 py-4 text-accent-blue font-medium text-[13px]">
                    {item.action ? labelize(item.action) : "—"}
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge value={item.status === 'allowed' ? 'APPROVED' : item.status} variant={statusVariant} />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      href={`/cases/${item.case_id}`}
                      className="inline-flex items-center gap-1.5 rounded-sm border border-border bg-background px-3 py-1.5 text-[11px] font-semibold text-primary transition hover:bg-surfaceHover"
                    >
                      <Search size={12} className="text-secondary" />
                      Inspect AI
                    </Link>
                  </td>
                </tr>
              );
            })}
            {!loading && !ordered.length && (
              <tr>
                <td colSpan={7} className="px-6 py-16 text-center text-secondary text-sm">
                  No recovery cases were created for this batch.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
